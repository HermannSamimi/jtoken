import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = {"name": "Alice", "age": 30, "active": True, "ref": None}


def run_cli(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "jtoken", *args],
        input=input_text,
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )


MONGO_SHELL_DOC = """
{
    "_id" : ObjectId("69ca983fbf8c8953c43c2407"),
    "tags" : [
        "forwarded",
        "drive"
    ]
}
"""


class TestCliEncode:
    def test_encode_from_stdin(self):
        result = run_cli("encode", input_text=json.dumps(SAMPLE))
        assert result.returncode == 0
        assert "name: Alice" in result.stdout
        assert "trues: active" in result.stdout
        assert "nulls: ref" in result.stdout

    def test_encode_from_file(self, tmp_path: Path):
        path = tmp_path / "input.json"
        path.write_text(json.dumps(SAMPLE), encoding="utf-8")
        result = run_cli("encode", "--file", str(path))
        assert result.returncode == 0
        assert "name: Alice" in result.stdout

    def test_encode_invalid_json_exits(self):
        result = run_cli("encode", "--input-format", "json", input_text="not json")
        assert result.returncode == 1
        assert "Invalid JSON input" in result.stderr

    def test_encode_writes_context_sidecar(self, tmp_path: Path):
        context_path = tmp_path / "ctx.json"
        result = run_cli(
            "encode",
            "--input-format",
            "mongo_shell",
            "--context-out",
            str(context_path),
            input_text=MONGO_SHELL_DOC,
        )
        assert result.returncode == 0
        context = json.loads(context_path.read_text(encoding="utf-8"))
        assert context["typed_values"]["_id"] == "object_id"
        assert "tags" in context["lists"]


class TestCliDecode:
    def test_decode_from_stdin(self):
        encoded = "name: Alice\nage: 30\ntrues: active\nnulls: ref"
        result = run_cli("decode", input_text=encoded)
        assert result.returncode == 0
        assert json.loads(result.stdout) == {
            "name": "Alice",
            "age": 30,
            "active": True,
            "ref": None,
        }

    def test_decode_from_file(self, tmp_path: Path):
        path = tmp_path / "input.jtoken"
        path.write_text("name: Alice", encoding="utf-8")
        result = run_cli("decode", "--file", str(path))
        assert result.returncode == 0
        assert json.loads(result.stdout) == {"name": "Alice"}

    def test_decode_invalid_input_exits(self):
        result = run_cli("decode", input_text="no separator here")
        assert result.returncode == 1
        assert result.stderr

    def test_decode_mongo_shell_with_context(self, tmp_path: Path):
        context_path = tmp_path / "ctx.json"
        encode_result = run_cli(
            "encode",
            "--input-format",
            "mongo_shell",
            "--context-out",
            str(context_path),
            input_text=MONGO_SHELL_DOC,
        )
        assert encode_result.returncode == 0
        decode_result = run_cli(
            "decode",
            "--output-format",
            "mongo_shell",
            "--context-in",
            str(context_path),
            input_text=encode_result.stdout,
        )
        assert decode_result.returncode == 0
        assert 'ObjectId("69ca983fbf8c8953c43c2407")' in decode_result.stdout


class TestCliStats:
    def test_stats_from_json_stdin(self):
        result = run_cli("stats", input_text=json.dumps(SAMPLE))
        assert result.returncode == 0
        assert "jtoken:" in result.stdout
        assert "json:" in result.stdout
        assert "saved:" in result.stdout

    def test_stats_from_encoded_stdin(self):
        encoded = "name: Alice\nage: 30\ntrues: active\nnulls: ref"
        result = run_cli("stats", input_text=encoded)
        assert result.returncode == 0
        assert "jtoken:" in result.stdout

    def test_stats_from_file(self, tmp_path: Path):
        path = tmp_path / "input.json"
        path.write_text(json.dumps(SAMPLE), encoding="utf-8")
        result = run_cli("stats", "--file", str(path), "--backend", "estimate")
        assert result.returncode == 0
        assert "saved:" in result.stdout


class TestCliCount:
    def test_count_from_json_stdin(self):
        result = run_cli("count", "--backend", "estimate", input_text=json.dumps(SAMPLE))
        assert result.returncode == 0
        assert int(result.stdout.strip()) > 0

    def test_count_from_encoded_stdin(self):
        encoded = "name: Alice\nage: 30\ntrues: active\nnulls: ref"
        result = run_cli("count", "--backend", "estimate", input_text=encoded)
        assert result.returncode == 0
        assert int(result.stdout.strip()) > 0

    def test_count_from_file(self, tmp_path: Path):
        path = tmp_path / "input.json"
        path.write_text(json.dumps(SAMPLE), encoding="utf-8")
        result = run_cli("count", "--file", str(path), "--backend", "estimate")
        assert result.returncode == 0
        assert int(result.stdout.strip()) > 0

    @pytest.mark.skipif(
        __import__("importlib").util.find_spec("tiktoken") is None,
        reason="tiktoken not installed",
    )
    def test_count_tiktoken_backend(self):
        result = run_cli(
            "count",
            "--backend",
            "tiktoken",
            input_text=json.dumps(SAMPLE),
        )
        assert result.returncode == 0
        assert int(result.stdout.strip()) > 0
