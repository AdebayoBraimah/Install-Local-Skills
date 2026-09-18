"""Zotero 10 local API, existing Keychain authorization, no redirect or write retry."""

import hashlib
from pathlib import Path
import re
from urllib.parse import urlparse, unquote
import requests
from .state import Blocked

BASE = "http://localhost:23119"


class LocalZotero:
    def __init__(self, http=None, credential=None):
        self.http = http or requests.Session()
        self.http.trust_env = False
        self.server_id = None
        _, headers = self.call("GET", "/api/", identity=False)
        self.server_id = headers.get("Zotero-Server-ID")
        if not self.server_id:
            raise Blocked("zotero_10_server_identity_required")
        if credential is None:
            from cli_anything.zotero.utils.auth import write_headers

            credential = write_headers
        self.credential = credential

    def call(
        self,
        method,
        path,
        *,
        body=None,
        form=None,
        binary=None,
        headers=None,
        identity=True,
        upload=False
    ):
        if not path.startswith("/api/") or "?" in path or ".." in path:
            raise Blocked("invalid_local_api_path")
        h = {"Zotero-API-Version": "3"}
        if identity:
            h["Zotero-Server-ID"] = self.server_id
        if method != "GET" and not upload:
            try:
                h.update(self.credential(self))
            except Exception:
                raise Blocked("zotero_authorization_required") from None
        h.update(headers or {})
        try:
            response = self.http.request(
                method,
                BASE + path,
                headers=h,
                json=body,
                data=form if form is not None else binary,
                timeout=(5, 45),
                allow_redirects=False,
            )
        except requests.RequestException:
            raise Blocked("zotero_timeout_or_unavailable") from None
        if identity and response.headers.get("Zotero-Server-ID") != self.server_id:
            raise Blocked("server_identity_changed")
        if response.status_code == 404:
            return None, response.headers
        if response.status_code in (401, 403):
            raise Blocked("zotero_authorization_required")
        if response.status_code in (409, 412, 428):
            raise Blocked("zotero_concurrent_change")
        if not 200 <= response.status_code < 300:
            raise Blocked("zotero_http_error", {"http_status": response.status_code})
        if response.status_code in (201, 204) and upload:
            return {}, response.headers
        try:
            return response.json(), response.headers
        except ValueError:
            return response.text, response.headers

    def all(self, kind):
        if kind not in ("items", "collections"):
            raise Blocked("invalid_object_type")
        data, _ = self.call("GET", "/api/users/0/" + kind)
        if not isinstance(data, list) or any(
            not isinstance(r, dict) or not isinstance(r.get("data"), dict) for r in data
        ):
            raise Blocked("invalid_zotero_inventory")
        return [{**r["data"], "key": r["key"], "version": r["version"]} for r in data]

    def get(self, kind, key):
        if kind not in ("items", "collections") or not re.fullmatch("[A-Z2-9]{8}", key):
            raise Blocked("invalid_object_key")
        data, _ = self.call("GET", "/api/users/0/" + kind + "/" + key)
        if data is None:
            return None
        if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
            raise Blocked("invalid_zotero_object")
        return {**data["data"], "key": data["key"], "version": data["version"]}

    def create(self, kind, data):
        if "key" in data or "version" in data:
            raise Blocked("server_generated_create_required")
        try:
            result, _ = self.call("POST", "/api/users/0/" + kind, body=[data])
        except Blocked as e:
            if e.code == "zotero_concurrent_change" or (
                e.code == "zotero_http_error"
                and 400 <= e.details.get("http_status", 0) < 500
                and e.details.get("http_status") != 408
            ):
                raise Blocked("zotero_create_rejected") from None
            raise
        if (
            isinstance(result, dict)
            and result.get("failed")
            and not result.get("successful")
        ):
            raise Blocked("zotero_create_rejected")
        if (
            not isinstance(result, dict)
            or result.get("failed")
            or len(result.get("successful", {})) != 1
        ):
            raise Blocked("zotero_create_failed_or_partial")
        actual = next(iter(result["successful"].values()))
        if not isinstance(actual, dict) or not re.fullmatch(
            "[A-Z2-9]{8}", str(actual.get("key", ""))
        ):
            raise Blocked("zotero_create_key_mismatch")
        return {"key": actual["key"]}

    def rename_collection(self, key, version, name):
        self.call(
            "PATCH",
            "/api/users/0/collections/" + key,
            body={"name": name},
            headers={"If-Unmodified-Since-Version": str(version)},
        )

    def collections(self, key, version, memberships):
        self.call(
            "PATCH",
            "/api/users/0/items/" + key,
            body={"collections": memberships},
            headers={"If-Unmodified-Since-Version": str(version)},
        )

    def file(self, key):
        data, _ = self.call("GET", "/api/users/0/items/" + key + "/file/view/url")
        if not data:
            return None
        if not isinstance(data, str):
            raise Blocked("invalid_attachment_file_url")
        p = urlparse(data)
        if p.scheme != "file" or p.netloc not in ("", "localhost"):
            raise Blocked("invalid_attachment_file_url")
        return unquote(p.path)

    def empty_attachment(self, key, version=None):
        row = self.get("items", key)
        path = self.file(key)
        if (
            not row
            or row.get("md5")
            or (path and Path(path).exists())
            or (version is not None and row["version"] != version)
        ):
            raise Blocked("attachment_changed_or_present")
        return row["version"]

    def upload(self, key, path):
        version = self.empty_attachment(key)
        data = Path(path).read_bytes()
        md5 = hashlib.md5(data).hexdigest()
        params = {
            "md5": md5,
            "filename": "paper.pdf",
            "filesize": str(len(data)),
            "mtime": str(int(Path(path).stat().st_mtime * 1000)),
            "contentType": "application/pdf",
        }
        route = "/api/users/0/items/" + key + "/file"
        details, _ = self.call(
            "POST", route, form=params, headers={"If-None-Match": "*"}
        )
        if not isinstance(details, dict):
            raise Blocked("invalid_upload_authorization")
        if details.get("exists"):
            raise Blocked("attachment_changed_or_present")
        p = urlparse(details.get("url", ""))
        token = details.get("uploadKey")
        if (
            p.scheme != "http"
            or p.netloc != "localhost:23119"
            or p.query
            or p.fragment
            or not isinstance(token, str)
            or not re.fullmatch("[A-Za-z0-9]{32}", token)
            or p.path != "/api/local/uploads/" + token
        ):
            raise Blocked("invalid_upload_destination")
        self.empty_attachment(key, version)
        self.call(
            "POST",
            p.path,
            binary=data,
            headers={"Content-Type": "application/octet-stream"},
            identity=False,
            upload=True,
        )
        self.empty_attachment(key, version)
        self.call("POST", route, form={"upload": token}, headers={"If-None-Match": "*"})
