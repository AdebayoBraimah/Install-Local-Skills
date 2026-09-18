import os
from pathlib import Path
import subprocess
import sys

from test_librarian import Library

LAUNCHER = Path.home() / ".agents/skills/lit-summarizer-cdx/scripts/batch-process.sh"
VAULT_WRAPPER = Path(
    "/Users/adebayobraimah/Library/CloudStorage/GoogleDrive-adebayo.braimah@gmail.com/My Drive/Obsidian/Academics/batch-process.sh"
)


def test_both_launchers_dry_run_without_codex_or_vault_writes(tmp_path):
    lib = Library(tmp_path)
    env = dict(
        os.environ,
        VAULT_PATH=str(lib.vault),
        OBSIDIAN_VAULT=str(lib.vault),
        LIBRARIAN_SNAPSHOT=str(lib.source),
        CODEX_BIN="/missing/codex",
        LIBRARIAN_PYTHON=sys.executable,
    )
    for entry in [LAUNCHER, VAULT_WRAPPER]:
        p = subprocess.run(
            ["bash", str(entry), "--dry-run", "--no-notify"],
            env=env,
            text=True,
            capture_output=True,
        )
        assert p.returncode == 0, (p.stdout, p.stderr)
        assert "AAAA0001" in p.stdout
        assert list(lib.vault.iterdir()) == []


def test_launcher_checks_durable_outcome_instead_of_codex_exit(tmp_path):
    lib = Library(tmp_path)
    stub = tmp_path / "codex"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    env = dict(
        os.environ,
        VAULT_PATH=str(lib.vault),
        LIBRARIAN_SNAPSHOT=str(lib.source),
        CODEX_BIN=str(stub),
        LIBRARIAN_PYTHON=sys.executable,
    )
    p = subprocess.run(
        ["bash", str(LAUNCHER), "--no-notify", "--zotero-only"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert p.returncode == 3, (p.stdout, p.stderr)
    assert "partial" in p.stdout


def test_no_work_skips_codex_and_notification_owner_is_single(tmp_path):
    from test_librarian import generate

    lib = Library(tmp_path)
    generate(lib)
    codex = tmp_path / "codex"
    calls = tmp_path / "calls"
    codex.write_text('#!/bin/sh\nprintf called >> "' + str(calls) + '"\nexit 0\n')
    codex.chmod(0o755)
    notifier = tmp_path / "notify"
    alerts = tmp_path / "alerts"
    notifier.write_text('#!/bin/sh\nprintf alert >> "' + str(alerts) + '"\n')
    notifier.chmod(0o755)
    env = dict(
        os.environ,
        VAULT_PATH=str(lib.vault),
        LIBRARIAN_SNAPSHOT=str(lib.source),
        CODEX_BIN=str(codex),
        LIBRARIAN_PYTHON=sys.executable,
        NTFY_SCRIPT=str(notifier),
    )
    p = subprocess.run(
        ["bash", str(LAUNCHER), "--zotero-only"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0 and not calls.exists()
    assert alerts.read_text() == "alert"
    p = subprocess.run(
        ["bash", str(LAUNCHER), "--zotero-only", "--no-notify"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0 and alerts.read_text() == "alert"


def test_new_files_only_and_option_validation(tmp_path):
    lib = Library(tmp_path)
    subprocess.run(["git", "init", str(lib.vault)], check=True, capture_output=True)
    notes = lib.vault / "Ideas/Research"
    notes.mkdir(parents=True)
    (notes / "new.md").write_text("New personal note\n")
    env = dict(
        os.environ,
        VAULT_PATH=str(lib.vault),
        CLI_ZOTERO="/missing/zotero",
        CODEX_BIN="/missing/codex",
        LIBRARIAN_PYTHON=sys.executable,
    )
    p = subprocess.run(
        ["bash", str(LAUNCHER), "--new-files-only", "--dry-run", "--no-notify"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0 and "new.md" in p.stdout
    assert not (lib.vault / ".obsidian-librarian").exists()
    for args in [
        ["--collection"],
        ["--item"],
        ["--unknown"],
        ["--new-files-only", "--collection", "X"],
    ]:
        p = subprocess.run(
            ["bash", str(LAUNCHER), *args], env=env, capture_output=True, text=True
        )
        assert p.returncode == 2
