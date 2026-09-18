import json
import subprocess
from pathlib import Path
import sys

CLI = Path(__file__).parents[1] / "scripts/lit_search.py"


def test_fixture_search_cli_persists_resume(tmp_path):
    f = tmp_path / "fixture.json"
    f.write_text(
        json.dumps(
            {
                "account": {
                    "account": {
                        "remaining_credits": 10000,
                        "monthly_allowance": 10000,
                        "current_month_usage": 0,
                    },
                    "api_usage": {"searches_this_hour": 0, "hourly_rate_limit": 10000},
                    "subscription": {
                        "period_start": "2026-09-01T00:00:00Z",
                        "period_end": "2026-10-01T00:00:00Z",
                    },
                },
                "responses": [
                    {
                        "params": {
                            "engine": "google_scholar",
                            "q": "test",
                            "num": 20,
                            "page": 1,
                        },
                        "data": {
                            "organic_results": [
                                {"title": "Test paper", "data_cid": "1"}
                            ]
                        },
                    }
                ],
            }
        )
    )
    args = [
        sys.executable,
        str(CLI),
        "search",
        "test",
        "--run-id",
        "p",
        "--state-dir",
        str(tmp_path / "state"),
        "--fixture",
        str(f),
    ]
    a = subprocess.run(args, capture_output=True, text=True)
    assert a.returncode == 0, a.stderr + a.stdout
    out = json.loads(a.stdout)
    assert out["status"] == "complete"
    b = subprocess.run(args, capture_output=True, text=True)
    assert json.loads(b.stdout)["usage"]["attempts"][0]["requests"] == 1


def test_legacy_adapters_keep_arrays_and_parent_run(tmp_path):
    import os

    fixture = {
        "account": {
            "account": {
                "remaining_credits": 10000,
                "monthly_allowance": 10000,
                "current_month_usage": 0,
            },
            "api_usage": {"searches_this_hour": 0, "hourly_rate_limit": 10000},
            "subscription": {
                "period_start": "2026-09-01T00:00:00Z",
                "period_end": "2026-10-01T00:00:00Z",
            },
        },
        "responses": [
            {
                "params": {
                    "engine": "google_scholar",
                    "q": "Unique seed",
                    "page": 1,
                    "num": 20,
                },
                "data": {
                    "organic_results": [
                        {
                            "title": "Unique seed",
                            "data_cid": "001",
                            "inline_links": {"cited_by": {"cites_id": "123"}},
                        }
                    ]
                },
            },
            {
                "params": {
                    "engine": "google_scholar",
                    "cites": "123",
                    "page": 1,
                    "num": 20,
                },
                "data": {
                    "organic_results": [{"title": "Citing paper", "data_cid": "002"}]
                },
            },
        ],
    }
    f = tmp_path / "fixture.json"
    f.write_text(json.dumps(fixture))
    seeds = tmp_path / "seeds.json"
    seeds.write_text('["Unique seed"]')
    env = {
        **os.environ,
        "LIT_SEARCH_FIXTURE": str(f),
        "LIT_SEARCH_STATE_DIR": str(tmp_path / "state"),
        "LIT_SEARCH_RUN_ID": "review-parent",
    }
    scripts = Path.home() / ".agents/skills/lit-survey-cdx/scripts"
    a = subprocess.run(
        [sys.executable, str(scripts / "scholarly_search.py"), "Unique seed", "15"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert a.returncode == 0, a.stderr
    assert isinstance(json.loads(a.stdout), list)
    b = subprocess.run(
        [sys.executable, str(scripts / "scholarly_snowball.py"), str(seeds), "10"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert b.returncode == 0, b.stderr
    assert json.loads(b.stdout)[0]["seed"] == "Unique seed"
    status = json.loads(b.stderr)
    assert status["run_id"] == "review-parent"
    assert status["usage"]["attempts"][0]["requests"] == 2
