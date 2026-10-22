from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import Artifact, ProcessorResult, RunContext, ToolDefinition
from .processors import PROCESSORS, Processor
from .registry import ToolRegistry
from .storage import WorkbenchStorage

_REFERENCE = re.compile(r"^\$\{([^}]+)\}$")


class ProcessorRegistry:
    def __init__(self, processors: dict[str, Processor] | None = None) -> None:
        self._processors = processors or PROCESSORS

    @property
    def names(self) -> set[str]:
        return set(self._processors)

    def get(self, name: str) -> Processor:
        try:
            return self._processors[name]
        except KeyError as exc:
            raise ValueError(f"未知处理器：{name}") from exc


class ExecutionService:
    """Application service that executes scripts and declarative workflows."""

    def __init__(
        self,
        tools: ToolRegistry,
        storage: WorkbenchStorage,
        processors: ProcessorRegistry | None = None,
    ) -> None:
        self.tools = tools
        self.storage = storage
        self.processors = processors or ProcessorRegistry()
        self.tools.validate_processors(self.processors.names)

    def run_tool(
        self,
        tool: ToolDefinition,
        input_files: dict[str, tuple[str, bytes]],
        params: dict[str, Any],
    ) -> tuple[str, ProcessorResult]:
        self._validate_input_ids(tool, input_files)
        effective_params = tool.normalize_params(params)
        context = self.storage.begin_run(tool, input_files, effective_params)
        try:
            if tool.kind == "workflow":
                result = self._run_workflow(tool, context, effective_params)
            else:
                result = self._run_script_step(
                    context=context,
                    step_id="main",
                    tool=tool,
                    input_paths={key: Path(value) for key, value in context.input_paths.items()},
                    params=effective_params,
                )
            self.storage.finish_run(context, tool, result)
        except Exception as exc:
            self.storage.fail_run(context, tool, exc)
            raise
        return context.run_id, result

    def _run_workflow(
        self, workflow: ToolDefinition, context: RunContext, params: dict[str, Any]
    ) -> ProcessorResult:
        step_results: dict[str, ProcessorResult] = {}
        collected_artifacts: dict[str, Artifact] = {}
        for step in workflow.steps:
            target = self.tools.get(step.uses)
            input_paths = {
                input_id: self._resolve_input(expression, workflow, context, step_results)
                for input_id, expression in step.inputs.items()
            }
            self._validate_input_ids(target, input_paths)
            step_params = target.normalize_params(self._resolve_value(step.params, params))
            result = self._run_script_step(
                context=context,
                step_id=step.id,
                tool=target,
                input_paths=input_paths,
                params=step_params,
            )
            step_results[step.id] = result
            for artifact_name, artifact in result.artifacts.items():
                collected_artifacts[f"{step.id}.{artifact_name}"] = artifact

        last_step = workflow.steps[-1]
        last_result = step_results[last_step.id]
        collected_artifacts["result"] = last_result.primary_artifact
        return ProcessorResult(
            artifacts=collected_artifacts,
            summary=(
                f"工作流完成：{len(workflow.steps)}/{len(workflow.steps)} 个步骤成功；"
                f"{last_result.summary}"
            ),
            preview=last_result.preview,
        )

    def _run_script_step(
        self,
        context: RunContext,
        step_id: str,
        tool: ToolDefinition,
        input_paths: dict[str, Path],
        params: dict[str, Any],
    ) -> ProcessorResult:
        if not tool.processor:
            raise ValueError(f"脚本 {tool.id!r} 未声明处理器")
        output_dir = Path(context.output_dir) / step_id
        output_dir.mkdir(parents=True, exist_ok=True)
        self.storage.begin_step(context, step_id, tool.id, input_paths)
        try:
            result = self.processors.get(tool.processor)(input_paths, output_dir, params)
            self._validate_artifacts(context, result)
        except Exception as exc:
            self.storage.fail_step(context, step_id, exc)
            raise
        self.storage.finish_step(context, step_id, result)
        return result

    @staticmethod
    def _validate_artifacts(context: RunContext, result: ProcessorResult) -> None:
        run_dir = Path(context.run_dir).resolve()
        if not result.artifacts:
            raise ValueError("处理器没有返回任何产物")
        for artifact in result.artifacts.values():
            artifact_path = Path(artifact.path).resolve()
            if not artifact_path.exists() or not artifact_path.is_file():
                raise ValueError(f"处理器返回的产物不存在：{artifact.path}")
            if not artifact_path.is_relative_to(run_dir):
                raise ValueError(f"处理器产物超出本次运行目录：{artifact.path}")

    @staticmethod
    def _resolve_input(
        expression: str,
        workflow: ToolDefinition,
        context: RunContext,
        step_results: dict[str, ProcessorResult],
    ) -> Path:
        match = _REFERENCE.fullmatch(expression)
        if not match:
            raise ValueError(f"工作流输入必须是完整引用：{expression}")
        reference = match.group(1)
        if reference.startswith("inputs."):
            input_id = reference.removeprefix("inputs.")
            try:
                return Path(context.input_paths[input_id])
            except KeyError as exc:
                raise ValueError(f"工作流没有输入：{input_id}") from exc
        parts = reference.split(".")
        if len(parts) >= 3 and parts[0] == "steps":
            step_id = parts[1]
            try:
                result = step_results[step_id]
            except KeyError as exc:
                raise ValueError(f"步骤输出尚不可用：{step_id}") from exc
            if parts[2] == "output":
                return Path(result.primary_artifact.path)
            if len(parts) == 4 and parts[2] == "outputs":
                try:
                    return Path(result.artifacts[parts[3]].path)
                except KeyError as exc:
                    raise ValueError(f"步骤 {step_id!r} 没有产物 {parts[3]!r}") from exc
        raise ValueError(f"无法解析工作流输入引用：{expression}")

    @staticmethod
    def _validate_input_ids(tool: ToolDefinition, inputs: dict[str, Any]) -> None:
        expected = {item.id for item in tool.inputs}
        actual = set(inputs)
        if expected == actual:
            return
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        details = []
        if missing:
            details.append(f"缺少：{', '.join(missing)}")
        if extra:
            details.append(f"多余：{', '.join(extra)}")
        raise ValueError(f"工具 {tool.id!r} 的输入不匹配（{'；'.join(details)}）")

    @classmethod
    def _resolve_value(cls, value: Any, params: dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {key: cls._resolve_value(item, params) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._resolve_value(item, params) for item in value]
        if isinstance(value, str):
            match = _REFERENCE.fullmatch(value)
            if match:
                reference = match.group(1)
                if reference.startswith("params."):
                    param_id = reference.removeprefix("params.")
                    try:
                        return params[param_id]
                    except KeyError as exc:
                        raise ValueError(f"缺少工作流参数：{param_id}") from exc
        return value
