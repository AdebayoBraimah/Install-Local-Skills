import json
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).parents[1] / "scripts/lit_search.py"


def test_import_fixture_cannot_reach_live_transport(tmp_path):
    # Deliberately missing input/fixture: guard must run before provider or API setup.
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "import",
            "--input",
            str(tmp_path / "absent"),
            "--select",
            "test",
            "--collection",
            "Review",
            "--selection-approved",
            "--fixture",
            str(tmp_path / "absent-fixture"),
            "--state-dir",
            str(tmp_path / "state"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3
    assert (
        json.loads(result.stdout)["remaining_work"][0]["reason"]
        == "fixture_import_not_supported_use_injected_test_transport"
    )


def test_import_requires_execution_choice(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "import",
            "--input",
            str(tmp_path / "absent"),
            "--select",
            "test",
            "--collection",
            "Review",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["run_id"] is None
    from lit_search import parser
    import pytest

    with pytest.raises(ValueError, match="--dry-run.*--selection-approved"):
        parser().parse_args(
            [
                "import",
                "--input",
                "absent",
                "--select",
                "test",
                "--collection",
                "Review",
            ]
        )
