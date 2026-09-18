"""Durable single-host state, locks and path confinement."""

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

VERSION = 1


def digest(value):
    if not isinstance(value, bytes):
        value = (
            value
            if isinstance(value, str)
            else json.dumps(value, sort_keys=True, ensure_ascii=False)
        ).encode()
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    return digest(path.read_bytes()) if path.is_file() else None


def confined(vault, relative):
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("Expected a relative path inside the vault")
    target = vault / p
    if not target.resolve().is_relative_to(vault.resolve()) or any(
        x.is_symlink() for x in [target, *target.parents] if x != vault.parent
    ):
        raise ValueError("Symlink or escaped destination")
    return target


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        value
        if isinstance(value, bytes)
        else (
            json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        ).encode()
    )
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        d = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(d)
        finally:
            os.close(d)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load(root):
    p = root / "state.json"
    state = (
        json.loads(p.read_text())
        if p.exists()
        else dict(
            schema_version=VERSION,
            revision=0,
            identity=None,
            items={},
            runs={},
            transactions={},
        )
    )
    if state.get("schema_version") != VERSION:
        raise ValueError("Unsupported state schema")
    return state


def save(root, state):
    state["revision"] += 1
    atomic(root / "state.json", state)


@contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    lockdir = root / "locks"
    lockdir.mkdir(exist_ok=True)
    with (lockdir / "writer.lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another librarian command holds the lock") from None
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
