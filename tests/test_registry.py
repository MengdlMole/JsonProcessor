import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from workbench.registry import ToolRegistry


class RegistryTests(unittest.TestCase):
    def test_registry_exposes_atomic_json_operations(self) -> None:
        registry = ToolRegistry(Path(__file__).resolve().parents[1] / "registry" / "tools.yaml")
        tool_ids = {tool.id for tool in registry.all()}
        self.assertTrue(
            {
                "json_pretty",
                "json_compact",
                "json_show_unicode",
                "json_escape_unicode",
                "json_remove_spaces",
                "json_remove_newlines",
                "json_remove_carriage_returns",
                "json_remove_tabs",
                "json_select_values",
                "json_filter_empty_values",
                "json_deduplicate_values",
                "json_rows_to_xlsx",
            }.issubset(tool_ids)
        )

    def test_workflow_rejects_incompatible_output_type(self) -> None:
        manifest = """
tools:
  - id: text_source
    name: Text source
    kind: script
    processor: text_remove_backslashes
    description: Text
    inputs: [{id: source_text, label: Text, content_type: text}]
    outputs: [{id: result, content_type: text}]
  - id: json_target
    name: JSON target
    kind: script
    processor: json_pretty
    description: JSON
    inputs: [{id: source_json, label: JSON, content_type: json}]
    outputs: [{id: result, content_type: json}]
  - id: broken
    name: Broken
    kind: workflow
    description: Broken
    inputs: [{id: source_text, label: Text, content_type: text}]
    outputs: [{id: result, content_type: json}]
    steps:
      - id: first
        uses: text_source
        inputs: {source_text: '${inputs.source_text}'}
      - id: second
        uses: json_target
        inputs: {source_json: '${steps.first.outputs.result}'}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tools.yaml"
            path.write_text(manifest)
            with self.assertRaisesRegex(ValueError, "cannot connect 'text'.*'json'"):
                ToolRegistry(path)

    def test_workbook_ui_metadata_is_declared_in_registry(self) -> None:
        registry = ToolRegistry(Path(__file__).resolve().parents[1] / "registry" / "tools.yaml")
        tool = registry.get("json_rows_fill_template_xlsx")
        template_input = next(item for item in tool.inputs if item.id == "template_xlsx")
        target_column = next(item for item in tool.parameters if item.id == "target_column")
        self.assertEqual(template_input.inspector, "xlsx")
        self.assertEqual(target_column.ui_control, "workbook_column")
        self.assertEqual(target_column.source_input, "template_xlsx")

    def test_duplicate_tool_ids_are_rejected(self) -> None:
        manifest = """
tools:
  - &tool
    id: duplicate
    name: First
    kind: script
    processor: json_pretty
    description: First
    inputs: [{id: source, label: Source, content_type: json}]
    outputs: [{id: result, content_type: json}]
  - <<: *tool
    name: Second
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tools.yaml"
            path.write_text(manifest)
            with self.assertRaisesRegex(ValidationError, "duplicate tool ids"):
                ToolRegistry(path)

    def test_workflow_cannot_reference_a_future_step(self) -> None:
        manifest = """
tools:
  - id: formatter
    name: Formatter
    kind: script
    processor: json_pretty
    description: Format
    inputs: [{id: source_json, label: Source, content_type: json}]
    outputs: [{id: result, content_type: json}]
  - id: broken
    name: Broken
    kind: workflow
    description: Broken workflow
    inputs: [{id: source_json, label: Source, content_type: json}]
    outputs: [{id: result, content_type: json}]
    steps:
      - id: first
        uses: formatter
        inputs: {source_json: '${steps.later.outputs.result}'}
      - id: later
        uses: formatter
        inputs: {source_json: '${inputs.source_json}'}
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tools.yaml"
            path.write_text(manifest)
            with self.assertRaisesRegex(ValueError, "unavailable step"):
                ToolRegistry(path)


if __name__ == "__main__":
    unittest.main()
