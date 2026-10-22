from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import ContentType, RegistryDocument, ToolDefinition, content_types_compatible


class ToolRegistry:
    def __init__(self, manifest_path: Path | list[Path]) -> None:
        self.manifest_paths = manifest_path if isinstance(manifest_path, list) else [manifest_path]
        definitions: list[dict[str, object]] = []
        for path in self.manifest_paths:
            if not path.exists():
                continue
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {"tools": []}
            document = RegistryDocument.model_validate(raw)
            definitions.extend(tool.model_dump() for tool in document.tools)
        document = RegistryDocument.model_validate({"tools": definitions})
        self._tools = {tool.id: tool for tool in document.tools}
        self._validate_workflow_references()

    def all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get(self, tool_id: str) -> ToolDefinition:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_id}") from exc

    def validate_processors(self, processor_names: set[str]) -> None:
        missing = sorted(
            str(tool.processor)
            for tool in self._tools.values()
            if tool.kind == "script" and tool.processor not in processor_names
        )
        if missing:
            raise ValueError(f"registry references unknown processors: {', '.join(missing)}")

    def _validate_workflow_references(self) -> None:
        for workflow in self._tools.values():
            if workflow.kind != "workflow":
                continue
            known_steps: set[str] = set()
            known_step_tools: dict[str, ToolDefinition] = {}
            for step in workflow.steps:
                target = self._tools.get(step.uses)
                if target is None:
                    raise ValueError(
                        f"workflow {workflow.id!r} references unknown tool {step.uses!r}"
                    )
                if target.kind != "script":
                    raise ValueError(
                        f"workflow {workflow.id!r} step {step.id!r} must reference a script"
                    )
                expected_inputs = {item.id for item in target.inputs}
                if set(step.inputs) != expected_inputs:
                    raise ValueError(
                        f"workflow {workflow.id!r} step {step.id!r} inputs must be "
                        f"{sorted(expected_inputs)!r}"
                    )
                prefix = "${steps."
                target_inputs = {item.id: item for item in target.inputs}
                for target_input_id, expression in step.inputs.items():
                    match = re.fullmatch(r"\$\{([^}]+)\}", expression)
                    if match is None:
                        raise ValueError(
                            f"workflow {workflow.id!r} step {step.id!r} has invalid input "
                            f"reference {expression!r}"
                        )
                    reference = match.group(1)
                    if reference.startswith("inputs."):
                        workflow_input_id = reference.removeprefix("inputs.")
                        workflow_inputs = {item.id: item for item in workflow.inputs}
                        if workflow_input_id not in workflow_inputs:
                            raise ValueError(
                                f"workflow {workflow.id!r} references unknown input "
                                f"{workflow_input_id!r}"
                            )
                        source_type = workflow_inputs[workflow_input_id].content_type
                    else:
                        source_type = self._step_reference_type(reference, known_step_tools)
                    target_type = target_inputs[target_input_id].content_type
                    if not content_types_compatible(source_type, target_type):
                        raise ValueError(
                            f"workflow {workflow.id!r} step {step.id!r} cannot connect "
                            f"{source_type!r} to input {target_input_id!r} ({target_type!r})"
                        )
                    if expression.startswith(prefix):
                        referenced_step = expression[len(prefix) :].split(".", 1)[0]
                        if referenced_step not in known_steps:
                            raise ValueError(
                                f"workflow {workflow.id!r} step {step.id!r} references "
                                f"unavailable step {referenced_step!r}"
                            )
                target_params = {item.id for item in target.parameters}
                unknown_params = set(step.params) - target_params
                if unknown_params:
                    raise ValueError(
                        f"workflow {workflow.id!r} step {step.id!r} has unknown parameters "
                        f"{sorted(unknown_params)!r}"
                    )
                known_steps.add(step.id)
                known_step_tools[step.id] = target
            last_step_tool = known_step_tools[workflow.steps[-1].id]
            if not content_types_compatible(
                last_step_tool.primary_output.content_type,
                workflow.primary_output.content_type,
            ):
                raise ValueError(
                    f"workflow {workflow.id!r} declares output "
                    f"{workflow.primary_output.content_type!r}, but its last step produces "
                    f"{last_step_tool.primary_output.content_type!r}"
                )

    @staticmethod
    def _step_reference_type(
        reference: str, known_step_tools: dict[str, ToolDefinition]
    ) -> ContentType:
        parts = reference.split(".")
        if len(parts) < 3 or parts[0] != "steps":
            raise ValueError(f"unsupported workflow input reference {reference!r}")
        step_id = parts[1]
        try:
            source_tool = known_step_tools[step_id]
        except KeyError as exc:
            raise ValueError(f"workflow references unavailable step {step_id!r}") from exc
        if parts[2] == "output":
            return source_tool.primary_output.content_type
        if len(parts) == 4 and parts[2] == "outputs":
            return source_tool.get_output(parts[3]).content_type
        raise ValueError(f"unsupported workflow output reference {reference!r}")
