from pathlib import Path
from litsearch.acquisition import verify_pdf, bundle
from litsearch.records import base
from litsearch.state import State
import pytest


def make_pdf(path, title):
    # Minimal valid PDF fixture with extractable text; no reportlab dependency.
    content = f"BT /F1 14 Tf 40 700 Td ({title}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream",
        b"<< /Title (" + title.encode() + b") >>",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(data)
    data += (
        b"xref\n0 7\n0000000000 65535 f \n"
        + b"".join(f"{n:010} 00000 n \n".encode() for n in offsets[1:])
        + f"trailer\n<< /Size 7 /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(data)


def record():
    r = base("A reliable paper title", "fixture", {"id": "1"}, {})
    r.update(authors=["A Researcher"], year=2024)
    return r


def test_pdf_signature_and_identity(tmp_path):
    p = tmp_path / "a.pdf"
    p.write_text("<html>oops</html>")
    assert verify_pdf(p, record())["status"] == "invalid"
    make_pdf(p, "An unrelated study")
    assert verify_pdf(p, record())["status"] == "mismatch"
    make_pdf(p, "A reliable paper title")
    assert verify_pdf(p, record())["status"] == "verified"


def test_bundle_existing_excluded_and_relative_attachments(tmp_path, monkeypatch):
    p = tmp_path / "a.pdf"
    make_pdf(p, "A reliable paper title")
    r = record()
    monkeypatch.setattr("litsearch.acquisition.zotero_match", lambda r: None)
    r["download"] = {"status": "verified", "path": str(p)}
    existing = dict(
        r, id="existing", zotero={"key": "ABC"}, citation_key="existing2024"
    )
    result = bundle(State(tmp_path / "data"), "r", [r, existing], [r["id"], "existing"])
    bib = (Path(result["bundle"]) / "library.bib").read_text()
    assert "file = {pdfs/" in bib and str(tmp_path) not in bib
    assert "existing2024" not in bib


def test_uncertain_never_attached(tmp_path, monkeypatch):
    monkeypatch.setattr("litsearch.acquisition.zotero_match", lambda r: None)
    r = record()
    p = tmp_path / "bad.pdf"
    make_pdf(p, "Unrelated study")
    r["download"] = {"status": "verified", "path": str(p)}
    result = bundle(State(tmp_path / "data"), "r", [r], [r["id"]])
    assert "file =" not in (Path(result["bundle"]) / "library.bib").read_text()


def test_citation_in_wrong_document_cannot_verify(tmp_path, monkeypatch):
    p = tmp_path / "wrong.pdf"
    make_pdf(p, "Unrelated document title")
    real = __import__("subprocess").run

    def command(args, **kwargs):
        if args[0] == "pdftotext":
            from subprocess import CompletedProcess

            return CompletedProcess(
                args,
                0,
                stdout="Unrelated document title\nReferences\nA reliable paper title",
                stderr="",
            )
        return real(args, **kwargs)

    monkeypatch.setattr("litsearch.acquisition.subprocess.run", command)
    assert verify_pdf(p, record())["status"] != "verified"


def test_bundle_refresh_after_import_changes_published_content(tmp_path, monkeypatch):
    matched = [None]
    monkeypatch.setattr("litsearch.acquisition.zotero_match", lambda r: matched[0])
    r = record()
    state = State(tmp_path / "state")
    first = bundle(state, "r", [r], [r["id"]])
    matched[0] = {"zotero": {"key": "IMPORTED", "attachments": []}}
    second = bundle(state, "r", [r], [r["id"]])
    assert Path(second["bundle"], "library.bib").read_text() == ""
    assert first["bundle"] != second["bundle"]


def test_fetch_unresolved_resume_stays_partial(tmp_path, monkeypatch):
    from litsearch.acquisition import fetch
    from types import SimpleNamespace

    monkeypatch.setattr("litsearch.acquisition.zotero_match", lambda r: None)
    p = SimpleNamespace(state=State(tmp_path))
    r = record()
    first = fetch(p, "r", [r], [r["id"]])
    second = fetch(p, "r", first["records"], [r["id"]])
    assert first["status"] == second["status"] == "partial"
    assert second["remaining_work"]


def test_existing_zotero_pdf_first_and_openalex_exhaustion(tmp_path, monkeypatch):
    from litsearch.acquisition import fetch
    from litsearch.state import Blocked
    from types import SimpleNamespace

    p = tmp_path / "existing.pdf"
    make_pdf(p, record()["title"])
    r = record()
    monkeypatch.setattr(
        "litsearch.acquisition.zotero_match",
        lambda r: {
            "zotero": {
                "key": "OLD",
                "attachments": [
                    {"full_path": str(p), "contentType": "application/pdf"}
                ],
            }
        },
    )
    monkeypatch.setattr(
        "litsearch.acquisition.download_bytes",
        lambda *a, **k: pytest.fail("existing PDF should avoid download"),
    )
    provider = SimpleNamespace(state=State(tmp_path / "state"))
    assert fetch(provider, "r", [r], [r["id"]])["status"] == "complete"
    monkeypatch.setattr("litsearch.acquisition.zotero_match", lambda r: None)
    r["pdf_locations"] = [
        {"url": "https://content.openalex.org/works/W1.pdf", "source": "openalex_cache"}
    ]

    def blocked(run):
        raise Blocked("daily_or_account_quota")

    provider.content_headers = blocked
    out = fetch(provider, "r", [r], [r["id"]])
    assert out["status"] == "partial"
    assert out["remaining_work"][0]["attempts"][0]["reason"] == "daily_or_account_quota"


def test_download_redirect_never_forwards_credentials(monkeypatch):
    from litsearch.acquisition import download_bytes
    from urllib.parse import urlparse

    calls = []

    class Response:
        def __init__(self, status, headers):
            self.status_code = status
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_content(self, *args):
            yield b"%PDF-example"

    class Session:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return (
                Response(302, {"Location": "https://publisher.example/p.pdf"})
                if len(calls) == 1
                else Response(200, {})
            )

        def close(self):
            pass

    monkeypatch.setattr("litsearch.acquisition.requests.Session", Session)
    monkeypatch.setattr("litsearch.acquisition.public_url", urlparse)
    download_bytes(
        "https://content.openalex.org/works/W1.pdf",
        headers={"Authorization": "Bearer secret"},
    )
    assert calls[0][1]["headers"] and calls[1][1]["headers"] == {}


@pytest.mark.parametrize("payload", ["<html>login</html>", "%PDF-broken"])
def test_invalid_download_stays_out_of_bundle(tmp_path, monkeypatch, payload):
    from litsearch.acquisition import fetch
    from types import SimpleNamespace

    monkeypatch.setattr("litsearch.acquisition.zotero_match", lambda r: None)
    monkeypatch.setattr(
        "litsearch.acquisition.download_bytes",
        lambda *a, **k: (payload.encode(), "https://example.org/file"),
    )
    r = record()
    r["pdf_locations"] = [{"url": "https://example.org/file", "source": "direct"}]
    state = State(tmp_path)
    out = fetch(SimpleNamespace(state=state), "r", [r], [r["id"]])
    assert out["status"] == "partial"
    b = bundle(state, "r", out["records"], [r["id"]])
    assert not list(Path(b["bundle"], "pdfs").iterdir())
