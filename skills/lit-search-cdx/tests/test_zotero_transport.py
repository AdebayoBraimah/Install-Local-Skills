from pathlib import Path
import pytest
from litsearch.state import Blocked
from litsearch.zotero_transport import LocalZotero


class Response:
    def __init__(self, data=None, status=200, headers=None, text=""):
        self.data = data
        self.status_code = status
        self.headers = headers or {"Zotero-Server-ID": "server"}
        self.text = text

    def json(self):
        return self.data


class HTTP:
    def __init__(self):
        self.calls = []
        self.queue = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.queue.pop(0) if self.queue else Response({})


def test_identity_mismatch_blocks_and_redirects_not_followed():
    http = HTTP()
    http.queue = [Response({}), Response({}, headers={"Zotero-Server-ID": "other"})]
    api = LocalZotero(
        http=http,
        credential=lambda c: {
            "Zotero-API-Key": "secret",
            "Zotero-Server-ID": c.server_id,
        },
    )
    with pytest.raises(Blocked, match="server_identity"):
        api.get("items", "ABCDEFGH")
    assert all(not k["allow_redirects"] for _, _, k in http.calls)


def test_unsynced_file_blocks_upload(tmp_path):
    http = HTTP()
    api = LocalZotero(http=http, credential=lambda c: {})
    p = tmp_path / "present.pdf"
    p.write_bytes(b"present")
    api.get = lambda *a: {"version": 1}
    api.file = lambda key: str(p)
    with pytest.raises(Blocked, match="attachment_changed_or_present"):
        api.upload("ABCDEFGH", p)
    assert len(http.calls) == 1


def test_upload_key_destination_is_restricted(tmp_path):
    http = HTTP()
    api = LocalZotero(http=http, credential=lambda c: {"Zotero-API-Key": "secret"})
    p = tmp_path / "paper.pdf"
    p.write_bytes(b"pdf")
    api.empty_attachment = lambda *args: 1
    http.queue = [
        Response({"url": "https://evil.example/upload", "uploadKey": "a" * 32})
    ]
    with pytest.raises(Blocked, match="invalid_upload_destination"):
        api.upload("ABCDEFGH", p)
    assert len(http.calls) == 2 and all(
        url.startswith("http://localhost:23119/") for _, url, _ in http.calls
    )


def test_file_appearing_before_register_blocks(tmp_path):
    http = HTTP()
    api = LocalZotero(http=http, credential=lambda c: {"Zotero-API-Key": "secret"})
    p = tmp_path / "paper.pdf"
    p.write_bytes(b"pdf")
    checks = [0]

    def check(*args):
        checks[0] += 1
        if checks[0] == 3:
            raise Blocked("attachment_changed_or_present")
        return 1

    api.empty_attachment = check
    http.queue = [
        Response(
            {
                "url": "http://localhost:23119/api/local/uploads/" + "a" * 32,
                "uploadKey": "a" * 32,
            }
        ),
        Response({}, 201),
    ]
    with pytest.raises(Blocked):
        api.upload("ABCDEFGH", p)
    assert len(http.calls) == 3
    upload = http.calls[-1]
    assert "Zotero-API-Key" not in upload[2]["headers"]


@pytest.mark.parametrize(
    "response,reason",
    [
        (Response({}, status=412), "zotero_create_rejected"),
        (
            Response({"successful": {}, "failed": {"0": {"code": 400}}}),
            "zotero_create_rejected",
        ),
        (Response({}, status=503), "zotero_http_error"),
        (Response({}, status=401), "zotero_authorization_required"),
        (Response("malformed"), "zotero_create_failed_or_partial"),
    ],
)
def test_create_preserves_rejected_versus_uncertain_outcomes(response, reason):
    http = HTTP()
    api = LocalZotero(http=http, credential=lambda c: {})
    http.queue = [response]
    with pytest.raises(Blocked, match=reason):
        api.create("items", {"itemType": "journalArticle", "title": "Reference"})


def test_server_generated_create_returns_key_and_omits_client_key():
    http = HTTP()
    api = LocalZotero(http=http, credential=lambda c: {})
    http.queue = [Response({"successful": {"0": {"key": "ABCDEFGH"}}, "failed": {}})]
    created = api.create("items", {"itemType": "journalArticle", "title": "Reference"})
    assert created["key"] == "ABCDEFGH"
    assert "key" not in http.calls[-1][2]["json"][0]
    with pytest.raises(Blocked, match="server_generated_create_required"):
        api.create("items", {"key": "ABCDEFGH", "version": 0})
