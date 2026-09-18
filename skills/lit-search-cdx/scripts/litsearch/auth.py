"""Credentials never appear in argv, persisted responses or diagnostic values."""

import os
from pathlib import Path
import re
import stat
from .state import Blocked


class Credentials:
    def __init__(self, path=None, backend=None):
        self.path = Path(path or Path.home() / "etc/search_api.env")
        if backend is None:
            from keyring.backends.macOS import Keyring

            backend = Keyring()
        self.backend = backend
        self.secrets = []

    def read_file(self):
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd) as f:
                s = os.fstat(f.fileno())
                if (
                    not stat.S_ISREG(s.st_mode)
                    or s.st_uid != os.getuid()
                    or s.st_mode & 0o077
                ):
                    raise Blocked("unsafe_credential_file")
                lines = f.read(65536).splitlines()
        except OSError:
            raise Blocked("credential_file_unavailable") from None
        values = []
        for line in lines:
            m = re.fullmatch(r"\s*(?:export\s+)?SEARCH_API_KEY\s*=\s*(.*?)\s*", line)
            if m:
                value = m[1]
                if value[:1] in ('"', "'"):
                    if len(value) < 2 or value[-1] != value[0]:
                        raise Blocked("invalid_credential_file")
                    value = value[1:-1]
                if not value or "\n" in value:
                    raise Blocked("invalid_credential_file")
                values.append(value)
        if len(values) != 1:
            raise Blocked("invalid_credential_file")
        self.secrets.append(values[0])
        return values[0]

    def get(self, provider):
        try:
            key = self.backend.get_password("lit-search-cdx", provider)
        except Exception:
            key = None
        if key:
            self.secrets.append(key)
            return key, "keychain"
        if provider == "searchapi":
            return self.read_file(), "file"
        return None, "anonymous"

    def import_file(self):
        value = self.read_file()
        try:
            self.backend.set_password("lit-search-cdx", "searchapi", value)
            if self.backend.get_password("lit-search-cdx", "searchapi") != value:
                raise ValueError()
        except Exception:
            raise Blocked("keychain_import_failed") from None
        return {"status": "complete", "source": "keychain", "backup": "protected_file"}

    def status(self):
        result = {}
        for name in ("searchapi", "openalex"):
            try:
                key, source = self.get(name)
                result[name] = {"available": bool(key), "source": source}
            except Blocked as e:
                result[name] = {"available": False, "reason": e.code}
        return result

    def clean(self, value):
        if isinstance(value, dict):
            return {
                k: self.clean(v)
                for k, v in value.items()
                if not re.search(r"api.?key|authorization|token|password", k, re.I)
            }
        if isinstance(value, list):
            return [self.clean(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            value = re.sub(
                r'(?i)(api_key|access_token|token)=([^&\s"\']+)',
                r"\1=[REDACTED]",
                value,
            )
        return value
