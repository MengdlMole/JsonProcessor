from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator

ContentType: TypeAlias = Literal["json", "json_array", "text", "xlsx"]


def content_types_compatible(source: ContentType, target: ContentType) -> bool:
    if source == target:
        return True
    return target == "json" and source == "json_array"


class InputDefinition(BaseModel):
    id: str
    label: str
    accept: list[str] = Field(default_factory=list)
    help: str = ""
    allow_paste: bool = False
    paste_label: str = "粘贴文本"
    placeholder: str = ""
    content_type: ContentType
    inspector: Literal["xlsx"] | None = None
    editor_actions: list[
        Literal[
            "pretty",
            "compact",
            "remove_newlines",
            "remove_carriage_returns",
            "remove_tabs",
            "remove_spaces",
            "unwrap_one_layer",
            "remove_backslashes",
            "show_unicode",
            "escape_unicode",
        ]
    ] = Field(default_factory=list)


class ParameterDefinition(BaseModel):
    id: str
    label: str
    type: Literal["text", "textarea", "integer", "boolean", "select"] = "text"
    default: Any = None
    help: str = ""
    options: list[str] = Field(default_factory=list)
    required: bool = True
    minimum: int | None = None
    maximum: int | None = None
    pattern: str | None = None
    ui_control: Literal["default", "workbook_sheet", "workbook_column"] = "default"
    source_input: str = ""
    sheet_parameter: str = "sheet_name"
    header_row_parameter: str = "header_row"

    @model_validator(mode="after")
    def validate_select(self) -> ParameterDefinition:
        if self.type == "select" and not self.options:
            raise ValueError(f"select parameter {self.id!r} must define options")
        return self

    def validate_value(self, value: Any) -> Any:
        if value is None:
            if self.required:
                raise ValueError(f"缺少必填参数：{self.id}")
            return None
        if self.type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"参数 {self.id!r} 必须是布尔值")
        if self.type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"参数 {self.id!r} 必须是整数")
            if self.minimum is not None and value < self.minimum:
                raise ValueError(f"参数 {self.id!r} 不能小于 {self.minimum}")
            if self.maximum is not None and value > self.maximum:
                raise ValueError(f"参数 {self.id!r} 不能大于 {self.maximum}")
        if self.type == "select" and value not in self.options:
            raise ValueError(f"参数 {self.id!r} 不在允许选项中")
        if self.pattern and isinstance(value, str) and re.fullmatch(self.pattern, value) is None:
            raise ValueError(f"参数 {self.id!r} 格式不正确")
        return value


class OutputDefinition(BaseModel):
    id: str = "result"
    label: str = "主要输出"
    content_type: ContentType


class WorkflowStepDefinition(BaseModel):
    id: str
    uses: str
    inputs: dict[str, str]
    params: dict[str, Any] = Field(default_factory=dict)

class ToolDefinition(BaseModel):
    id: str
    name: str
    kind: Literal["script", "workflow"] = "script"
    description: str
    processor: str | None = None
    version: str = "1"
    tags: list[str] = Field(default_factory=list)
    inputs: list[InputDefinition]
    outputs: list[OutputDefinition]
    parameters: list[ParameterDefinition] = Field(default_factory=list)
    steps: list[WorkflowStepDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_execution_definition(self) -> ToolDefinition:
        if self.kind == "script" and not self.processor:
            raise ValueError(f"script {self.id!r} must define processor")
        if self.kind == "workflow" and not self.steps:
            raise ValueError(f"workflow {self.id!r} must define steps")
        if not self.inputs:
            raise ValueError(f"tool {self.id!r} must define at least one input")
        input_ids = [input_definition.id for input_definition in self.inputs]
        if len(input_ids) != len(set(input_ids)):
            raise ValueError(f"tool {self.id!r} contains duplicate input ids")
        parameter_ids = [parameter.id for parameter in self.parameters]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError(f"tool {self.id!r} contains duplicate parameter ids")
        output_ids = [output.id for output in self.outputs]
        if len(output_ids) != len(set(output_ids)):
            raise ValueError(f"tool {self.id!r} contains duplicate output ids")
        if not self.outputs:
            raise ValueError(f"tool {self.id!r} must define at least one output")
        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError(f"workflow {self.id!r} contains duplicate step ids")
        return self

    def normalize_params(self, supplied: dict[str, Any]) -> dict[str, Any]:
        known = {parameter.id for parameter in self.parameters}
        unknown = sorted(set(supplied) - known)
        if unknown:
            raise ValueError(f"工具 {self.id!r} 收到未知参数：{', '.join(unknown)}")
        normalized: dict[str, Any] = {}
        for parameter in self.parameters:
            value = supplied.get(parameter.id, parameter.default)
            normalized[parameter.id] = parameter.validate_value(value)
        return normalized

    @property
    def primary_input(self) -> InputDefinition:
        return self.inputs[0]

    @property
    def primary_output(self) -> OutputDefinition:
        return self.outputs[0]

    def get_output(self, output_id: str) -> OutputDefinition:
        try:
            return next(output for output in self.outputs if output.id == output_id)
        except StopIteration as exc:
            raise ValueError(f"工具 {self.id!r} 没有输出 {output_id!r}") from exc


class RegistryDocument(BaseModel):
    tools: list[ToolDefinition]

    @model_validator(mode="after")
    def validate_unique_tool_ids(self) -> RegistryDocument:
        tool_ids = [tool.id for tool in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("registry contains duplicate tool ids")
        return self


class Artifact(BaseModel):
    name: str
    path: str
    media_type: str = "application/octet-stream"
    size: int = 0
    sha256: str = ""

    @classmethod
    def from_path(
        cls, name: str, path: Path, media_type: str = "application/octet-stream"
    ) -> Artifact:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        return cls(
            name=name,
            path=str(path),
            media_type=media_type,
            size=size,
            sha256=digest.hexdigest(),
        )


class ProcessorResult(BaseModel):
    artifacts: dict[str, Artifact]
    summary: str
    preview: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_path(
        cls,
        output_path: Path,
        summary: str,
        preview: list[dict[str, Any]] | None = None,
        media_type: str = "application/octet-stream",
    ) -> ProcessorResult:
        return cls(
            artifacts={"result": Artifact.from_path("result", output_path, media_type)},
            summary=summary,
            preview=preview or [],
        )

    @property
    def primary_artifact(self) -> Artifact:
        if "result" in self.artifacts:
            return self.artifacts["result"]
        return next(iter(self.artifacts.values()))

class StepRunRecord(BaseModel):
    step_id: str
    tool_id: str
    status: Literal["running", "success", "failed"]
    started_at: str
    finished_at: str | None = None
    input_path: str
    output_path: str | None = None
    summary: str | None = None
    error: str | None = None


class RunContext(BaseModel):
    run_id: str
    run_dir: str
    input_paths: dict[str, str]
    output_dir: str
    input_metadata: dict[str, dict[str, Any]]
    started_at: str
    params: dict[str, Any]
    steps: list[StepRunRecord] = Field(default_factory=list)

    @property
    def input_path(self) -> str:
        return next(iter(self.input_paths.values()))
