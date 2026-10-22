from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from .models import ProcessorResult, RunContext, StepRunRecord, ToolDefinition


class WorkbenchStorage:
    """Persistence adapter for runs, step records, artifacts and presets."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.runs_dir = data_dir / "runs"
        self.db_path = data_dir / "workbench.db"
        self.presets_path = data_dir / "presets.json"
        self.custom_tools_path = data_dir / "custom_tools.yaml"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    tool_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    input_name TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    output_path TEXT,
                    summary TEXT,
                    error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS run_inputs (
                    run_id TEXT NOT NULL,
                    input_id TEXT NOT NULL,
                    input_name TEXT NOT NULL,
                    input_sha256 TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    PRIMARY KEY (run_id, input_id),
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS step_runs (
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    input_path TEXT NOT NULL,
                    output_path TEXT,
                    summary TEXT,
                    error TEXT,
                    PRIMARY KEY (run_id, step_id),
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                )
                """
            )

    def begin_run(
        self,
        tool: ToolDefinition,
        input_files: dict[str, tuple[str, bytes]],
        params: dict[str, Any],
    ) -> RunContext:
        now = datetime.now(UTC)
        run_id = now.strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
        run_dir = self.runs_dir / run_id
        input_dir = run_dir / "inputs"
        output_dir = run_dir / "outputs"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        input_paths: dict[str, str] = {}
        input_metadata: dict[str, dict[str, Any]] = {}
        for input_id, (input_name, input_bytes) in input_files.items():
            safe_input_name = Path(input_name).name or "input.dat"
            item_dir = input_dir / input_id
            item_dir.mkdir(parents=True)
            input_path = item_dir / safe_input_name
            input_path.write_bytes(input_bytes)
            digest = hashlib.sha256(input_bytes).hexdigest()
            input_paths[input_id] = str(input_path)
            input_metadata[input_id] = {
                "name": safe_input_name,
                "sha256": digest,
                "path": str(input_path),
            }

        first_metadata = next(iter(input_metadata.values()))

        context = RunContext(
            run_id=run_id,
            run_dir=str(run_dir),
            input_paths=input_paths,
            output_dir=str(output_dir),
            input_metadata=input_metadata,
            started_at=now.isoformat(),
            params=params,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    id, tool_id, tool_name, kind, status, started_at,
                    input_name, input_sha256, params_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    tool.id,
                    tool.name,
                    tool.kind,
                    "running",
                    context.started_at,
                    ", ".join(item["name"] for item in input_metadata.values()),
                    first_metadata["sha256"],
                    json.dumps(params, ensure_ascii=False),
                ),
            )
            connection.executemany(
                """
                INSERT INTO run_inputs (
                    run_id, input_id, input_name, input_sha256, input_path
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        input_id,
                        metadata["name"],
                        metadata["sha256"],
                        metadata["path"],
                    )
                    for input_id, metadata in input_metadata.items()
                ],
            )
        return context

    def begin_step(
        self,
        context: RunContext,
        step_id: str,
        tool_id: str,
        input_paths: dict[str, Path],
    ) -> None:
        started_at = datetime.now(UTC).isoformat()
        serialized_paths = json.dumps(
            {input_id: str(path) for input_id, path in input_paths.items()},
            ensure_ascii=False,
        )
        context.steps.append(
            StepRunRecord(
                step_id=step_id,
                tool_id=tool_id,
                status="running",
                started_at=started_at,
                input_path=serialized_paths,
            )
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO step_runs (
                    run_id, step_id, tool_id, status, started_at, input_path
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (context.run_id, step_id, tool_id, "running", started_at, serialized_paths),
            )

    def finish_step(self, context: RunContext, step_id: str, result: ProcessorResult) -> None:
        finished_at = datetime.now(UTC).isoformat()
        output_path = result.primary_artifact.path
        record = self._find_step(context, step_id)
        record.status = "success"
        record.finished_at = finished_at
        record.output_path = output_path
        record.summary = result.summary
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE step_runs
                SET status = ?, finished_at = ?, output_path = ?, summary = ?
                WHERE run_id = ? AND step_id = ?
                """,
                (
                    "success",
                    finished_at,
                    output_path,
                    result.summary,
                    context.run_id,
                    step_id,
                ),
            )

    def fail_step(self, context: RunContext, step_id: str, error: Exception) -> None:
        finished_at = datetime.now(UTC).isoformat()
        message = f"{type(error).__name__}: {error}"
        record = self._find_step(context, step_id)
        record.status = "failed"
        record.finished_at = finished_at
        record.error = message
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE step_runs SET status = ?, finished_at = ?, error = ?
                WHERE run_id = ? AND step_id = ?
                """,
                ("failed", finished_at, message, context.run_id, step_id),
            )

    def finish_run(
        self, context: RunContext, tool: ToolDefinition, result: ProcessorResult
    ) -> None:
        finished_at = datetime.now(UTC).isoformat()
        output_path = result.primary_artifact.path
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = ?, finished_at = ?, output_path = ?, summary = ?
                WHERE id = ?
                """,
                ("success", finished_at, output_path, result.summary, context.run_id),
            )
        self._write_manifest(context, tool, "success", result, None, finished_at)

    def fail_run(self, context: RunContext, tool: ToolDefinition, error: Exception) -> None:
        finished_at = datetime.now(UTC).isoformat()
        message = f"{type(error).__name__}: {error}"
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
                ("failed", finished_at, message, context.run_id),
            )
        self._write_manifest(context, tool, "failed", None, message, finished_at)

    @staticmethod
    def _find_step(context: RunContext, step_id: str) -> StepRunRecord:
        return next(step for step in context.steps if step.step_id == step_id)

    @staticmethod
    def _write_manifest(
        context: RunContext,
        tool: ToolDefinition,
        status: str,
        result: ProcessorResult | None,
        error: str | None,
        finished_at: str,
    ) -> None:
        document = {
            "run_id": context.run_id,
            "tool_id": tool.id,
            "tool_version": tool.version,
            "kind": tool.kind,
            "status": status,
            "started_at": context.started_at,
            "finished_at": finished_at,
            "inputs": context.input_metadata,
            "effective_params": context.params,
            "steps": [step.model_dump() for step in context.steps],
            "result": result.model_dump() if result else None,
            "error": error,
        }
        (Path(context.run_dir) / "run.json").write_text(
            json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def list_step_runs(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM step_runs WHERE run_id = ? ORDER BY started_at", (run_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def list_run_inputs(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM run_inputs WHERE run_id = ? ORDER BY input_id", (run_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def load_run_manifest(self, run_id: str) -> dict[str, Any] | None:
        path = self.runs_dir / run_id / "run.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_presets(self) -> dict[str, dict[str, dict[str, Any]]]:
        if not self.presets_path.exists():
            return {}
        return json.loads(self.presets_path.read_text(encoding="utf-8"))

    def save_preset(self, tool_id: str, name: str, params: dict[str, Any]) -> None:
        presets = self.load_presets()
        presets.setdefault(tool_id, {})[name] = params
        temporary = self.presets_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.presets_path)

    def delete_preset(self, tool_id: str, name: str) -> bool:
        presets = self.load_presets()
        tool_presets = presets.get(tool_id, {})
        if name not in tool_presets:
            return False
        del tool_presets[name]
        if not tool_presets:
            presets.pop(tool_id, None)
        temporary = self.presets_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.presets_path)
        return True

    def load_custom_tools(self) -> list[ToolDefinition]:
        if not self.custom_tools_path.exists():
            return []
        raw = yaml.safe_load(self.custom_tools_path.read_text(encoding="utf-8")) or {"tools": []}
        return [ToolDefinition.model_validate(item) for item in raw.get("tools", [])]

    def save_custom_tool(self, tool: ToolDefinition) -> None:
        tools = {item.id: item for item in self.load_custom_tools()}
        tools[tool.id] = tool
        document = {"tools": [item.model_dump(exclude_none=True) for item in tools.values()]}
        temporary = self.custom_tools_path.with_suffix(".tmp")
        temporary.write_text(
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        temporary.replace(self.custom_tools_path)

    def delete_custom_tool(self, tool_id: str) -> bool:
        tools = {item.id: item for item in self.load_custom_tools()}
        if tool_id not in tools:
            return False
        del tools[tool_id]
        document = {"tools": [item.model_dump(exclude_none=True) for item in tools.values()]}
        temporary = self.custom_tools_path.with_suffix(".tmp")
        temporary.write_text(
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        temporary.replace(self.custom_tools_path)
        return True
