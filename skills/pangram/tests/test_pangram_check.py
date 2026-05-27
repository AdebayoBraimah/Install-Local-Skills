from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

import pangram_check


VALID_RESPONSE = {
    "headline": "AI Detected",
    "prediction_short": "Mixed",
    "fraction_ai": 0.7,
    "fraction_ai_assisted": 0.2,
    "fraction_human": 0.1,
    "num_ai_segments": 7,
    "num_ai_assisted_segments": 2,
    "num_human_segments": 1,
    "dashboard_link": "https://dashboard.example/report",
    "windows": [
        {
            "text": "example",
            "label": "AI-Generated",
            "ai_assistance_score": 0.85,
            "confidence": "High",
            "start_index": 0,
            "end_index": 7,
            "word_count": 1,
            "token_length": 1,
        }
    ],
}


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200, reason: str = "OK") -> None:
        self.payload = payload
        self.status = status
        self.reason = reason

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


class RecordingOpener:
    def __init__(self, payloads: list[Any] | None = None) -> None:
        self.payloads = list(payloads or [VALID_RESPONSE])
        self.requests = []
        self.timeouts = []

    def __call__(self, request: Any, timeout: int) -> FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        payload = self.payloads.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return FakeResponse(payload)


class TTYInput(io.StringIO):
    def isatty(self) -> bool:
        return True


class RaisingInput(io.StringIO):
    def read(self, *args: object, **kwargs: object) -> str:
        raise AssertionError("stdin should not be read")

    def isatty(self) -> bool:
        return False


def isolated_project(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".git").mkdir()
    return root


def response_with(**updates: Any) -> dict[str, Any]:
    response = dict(VALID_RESPONSE)
    response.update(updates)
    if "windows" not in updates:
        response["windows"] = [dict(VALID_RESPONSE["windows"][0])]
    return response


def test_call_pangram_api_posts_v3_body_headers_and_timeout() -> None:
    opener = RecordingOpener()

    result = pangram_check.call_pangram_api(
        "hello",
        public_dashboard_link=True,
        api_key="pg_secretabcd",
        opener=opener,
        timeout=30,
    )

    request = opener.requests[0]
    headers = dict(request.header_items())
    body = json.loads(request.data.decode("utf-8"))
    assert request.full_url == pangram_check.PANGRAM_V3_URL
    assert request.get_method() == "POST"
    assert headers["Content-type"] == "application/json"
    assert headers["X-api-key"] == "pg_secretabcd"
    assert body == {"text": "hello", "public_dashboard_link": True}
    assert opener.timeouts == [30]
    assert result["headline"] == "AI Detected"


def test_response_validation_rejects_missing_or_invalid_required_fields() -> None:
    with pytest.raises(pangram_check.PangramResponseError):
        pangram_check.validate_pangram_response(response_with(headline=123))
    with pytest.raises(pangram_check.PangramResponseError):
        pangram_check.validate_pangram_response(response_with(fraction_ai="0.7"))
    with pytest.raises(pangram_check.PangramResponseError):
        pangram_check.validate_pangram_response(response_with(num_ai_segments=True))
    with pytest.raises(pangram_check.PangramResponseError):
        pangram_check.validate_pangram_response(response_with(windows=[{"ai_assistance_score": 2.0}]))


def test_malformed_json_and_network_errors_are_sanitized() -> None:
    key = "pg_supersecretabcd"
    with pytest.raises(pangram_check.PangramResponseError) as malformed:
        pangram_check.call_pangram_api("hello", False, key, opener=RecordingOpener([b"{bad json"]))
    assert key not in str(malformed.value)

    with pytest.raises(pangram_check.PangramAPIError) as failed:
        pangram_check.call_pangram_api(
            "hello",
            False,
            key,
            opener=RecordingOpener([OSError(f"boom {key}")]),
        )
    assert key not in str(failed.value)
    assert "pg_****abcd" in str(failed.value)


def test_chunk_text_preserves_reconstruction_offsets_and_split_preferences() -> None:
    paragraph_text = "First paragraph.\n\nSecond paragraph has more words."
    paragraph_chunks = pangram_check.chunk_text(paragraph_text, max_chars=25)
    assert paragraph_chunks[0] == (0, "First paragraph.\n\n")
    assert "".join(chunk for _, chunk in paragraph_chunks) == paragraph_text

    sentence_text = "One sentence. Two sentence? Three sentence!"
    sentence_chunks = pangram_check.chunk_text(sentence_text, max_chars=20)
    assert sentence_chunks[0] == (0, "One sentence.")
    assert "".join(chunk for _, chunk in sentence_chunks) == sentence_text

    hard_chunks = pangram_check.chunk_text("abcdefghij", max_chars=4)
    assert hard_chunks == [(0, "abcd"), (4, "efgh"), (8, "ij")]


def test_aggregate_chunk_responses_weights_counts_predictions_windows_and_links() -> None:
    text = "aaaaabbbbbbbbbbbbbbb"
    first = response_with(
        prediction_short="AI",
        fraction_ai=1.0,
        fraction_ai_assisted=0.0,
        fraction_human=0.0,
        num_ai_segments=1,
        num_ai_assisted_segments=0,
        num_human_segments=0,
        dashboard_link="https://dash.example/1",
        windows=[
            {
                "ai_assistance_score": 0.4,
                "start_index": 1,
                "end_index": 4,
                "label": "AI",
                "confidence": "Medium",
            }
        ],
    )
    second = response_with(
        prediction_short="Human",
        fraction_ai=0.0,
        fraction_ai_assisted=0.2,
        fraction_human=0.8,
        num_ai_segments=0,
        num_ai_assisted_segments=2,
        num_human_segments=3,
        dashboard_link="https://dash.example/2",
        windows=[
            {
                "ai_assistance_score": 0.9,
                "start_index": 2,
                "end_index": 5,
                "label": "AI",
                "confidence": "High",
            }
        ],
    )

    result = pangram_check.aggregate_chunk_responses(text, [(0, text[:5], first), (5, text[5:], second)])

    assert result["headline"] == "Multi-chunk Pangram analysis"
    assert result["prediction_short"] == "Mixed"
    assert result["fraction_ai"] == pytest.approx(0.25)
    assert result["fraction_ai_assisted"] == pytest.approx(0.15)
    assert result["fraction_human"] == pytest.approx(0.60)
    assert result["num_ai_segments"] == 1
    assert result["num_ai_assisted_segments"] == 2
    assert result["num_human_segments"] == 3
    assert result["windows"][0]["start_index"] == 7
    assert result["windows"][0]["end_index"] == 10
    assert result["chunk_dashboard_links"] == [
        {"chunk_index": 0, "start_offset": 0, "dashboard_link": "https://dash.example/1"},
        {"chunk_index": 1, "start_offset": 5, "dashboard_link": "https://dash.example/2"},
    ]


def test_analyze_text_submits_multiple_chunks_and_aggregates() -> None:
    opener = RecordingOpener(
        [
            response_with(prediction_short="Human", fraction_human=1.0, fraction_ai=0.0, fraction_ai_assisted=0.0),
            response_with(prediction_short="Human", fraction_human=1.0, fraction_ai=0.0, fraction_ai_assisted=0.0),
        ]
    )

    result = pangram_check.analyze_text(
        "abcd efgh",
        public_dashboard_link=False,
        api_key="pg_secretabcd",
        opener=opener,
        max_chars=5,
    )

    assert len(opener.requests) == 2
    assert json.loads(opener.requests[0].data.decode("utf-8"))["text"] == "abcd "
    assert result["prediction_short"] == "Human"
    assert result["num_chunks"] == 2


def test_cli_json_text_input_uses_env_key_and_ignores_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PANGRAM_API_KEY", "pg_envsecretabcd")
    opener = RecordingOpener()
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = pangram_check.main(
        ["--text", "hello", "--json", "--project-root", str(isolated_project(tmp_path))],
        stdin=RaisingInput("ignored"),
        stdout=stdout,
        stderr=stderr,
        opener=opener,
    )

    assert code == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue())["headline"] == "AI Detected"
    assert dict(opener.requests[0].header_items())["X-api-key"] == "pg_envsecretabcd"


def test_cli_validates_empty_input_before_key_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_key_lookup(*args: object, **kwargs: object) -> object:
        raise AssertionError("key discovery should not run")

    monkeypatch.setattr(pangram_check, "find_pangram_api_key", fail_key_lookup)
    stderr = io.StringIO()

    code = pangram_check.main(["--text", "   "], stdout=io.StringIO(), stderr=stderr)

    assert code == 2
    assert "Input text is empty" in stderr.getvalue()


def test_cli_missing_key_does_not_prompt_or_call_api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PANGRAM_API_KEY", raising=False)
    opener = RecordingOpener()
    stderr = io.StringIO()

    code = pangram_check.main(
        ["--text", "hello", "--project-root", str(isolated_project(tmp_path))],
        stdout=io.StringIO(),
        stderr=stderr,
        opener=opener,
    )

    assert code == 2
    assert pangram_check.MISSING_KEY_MESSAGE in stderr.getvalue()
    assert opener.requests == []


def test_cli_prompt_key_uses_prompt_fn_after_discovery_miss(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PANGRAM_API_KEY", raising=False)
    opener = RecordingOpener()

    code = pangram_check.main(
        ["--text", "hello", "--prompt-key", "--project-root", str(isolated_project(tmp_path))],
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        opener=opener,
        prompt_fn=lambda prompt: "pg_promptsecretabcd",
        has_tty_fn=lambda: True,
    )

    assert code == 0
    assert dict(opener.requests[0].header_items())["X-api-key"] == "pg_promptsecretabcd"


def test_cli_prompt_key_without_tty_fails_without_prompt_or_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PANGRAM_API_KEY", raising=False)
    opener = RecordingOpener()

    def fail_prompt(prompt: str) -> str:
        raise AssertionError("prompt should not run")

    code = pangram_check.main(
        ["--text", "hello", "--prompt-key", "--project-root", str(isolated_project(tmp_path))],
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        opener=opener,
        prompt_fn=fail_prompt,
        has_tty_fn=lambda: False,
    )

    assert code == 2
    assert opener.requests == []


def test_cli_reads_file_and_non_tty_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PANGRAM_API_KEY", "pg_envsecretabcd")
    text_file = tmp_path / "draft.txt"
    text_file.write_text("file text", encoding="utf-8")

    file_opener = RecordingOpener()
    stdin_opener = RecordingOpener()

    assert pangram_check.main(["--file", str(text_file)], stdout=io.StringIO(), stderr=io.StringIO(), opener=file_opener) == 0
    assert json.loads(file_opener.requests[0].data.decode("utf-8"))["text"] == "file text"

    assert pangram_check.main([], stdin=io.StringIO("stdin text"), stdout=io.StringIO(), stderr=io.StringIO(), opener=stdin_opener) == 0
    assert json.loads(stdin_opener.requests[0].data.decode("utf-8"))["text"] == "stdin text"


def test_cli_tty_without_input_exits_without_blocking(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PANGRAM_API_KEY", raising=False)
    stderr = io.StringIO()

    code = pangram_check.main(
        ["--project-root", str(isolated_project(tmp_path))],
        stdin=TTYInput(),
        stdout=io.StringIO(),
        stderr=stderr,
    )

    assert code == 2
    assert "No input text provided" in stderr.getvalue()


def test_cli_conflicting_text_and_file_exits_2(tmp_path: Path) -> None:
    text_file = tmp_path / "draft.txt"
    text_file.write_text("file text", encoding="utf-8")

    with pytest.raises(SystemExit) as exited:
        pangram_check.main(["--text", "hello", "--file", str(text_file)])

    assert exited.value.code == 2


def test_cli_public_dashboard_link_and_json_error_sanitization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    key = "pg_supersecretabcd"
    monkeypatch.setenv("PANGRAM_API_KEY", key)
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = pangram_check.main(
        ["--text", "hello", "--public-dashboard-link", "--json", "--project-root", str(isolated_project(tmp_path))],
        stdout=stdout,
        stderr=stderr,
        opener=RecordingOpener([urllib.error.URLError(f"bad {key}")]),
    )

    assert code == 4
    assert stdout.getvalue() == ""
    error = json.loads(stderr.getvalue())
    assert error["exit_code"] == 4
    assert key not in error["error"]
    assert "pg_****abcd" in error["error"]
