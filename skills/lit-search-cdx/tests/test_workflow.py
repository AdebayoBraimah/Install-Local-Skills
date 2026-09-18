from litsearch.workflow import Workflow
from litsearch.state import State


class FixtureProvider:
    def __init__(self, root):
        self.state = State(root)
        self.calls = []
        self.sources = {}
        self.accounts = {}

    def request(self, provider, run, params=None, path="works", refresh=False):
        self.calls.append((provider, params, path))
        if provider == "searchapi":
            if params.get("q") == "ambiguous":
                return {
                    "organic_results": [
                        {
                            "title": "ambiguous",
                            "data_cid": str(i),
                            "inline_links": {"cited_by": {"cites_id": str(i)}},
                        }
                        for i in range(2)
                    ]
                }
            if params.get("q") == "missing":
                return {"organic_results": []}
            return {
                "organic_results": [
                    {
                        "title": "Paper",
                        "data_cid": str(params["page"]) + str(i),
                        "inline_links": {"cited_by": {"cites_id": "123"}},
                    }
                    for i in range(params["num"])
                ]
            }
        if path == "works/W1":
            return {
                "id": "https://openalex.org/W1",
                "title": "Seed",
                "referenced_works": ["https://openalex.org/W2"],
            }
        if path == "works/W2":
            return {"id": "https://openalex.org/W2", "title": "Reference"}
        return {"results": []}


def test_pagination_and_versions_exclude_query(tmp_path):
    p = FixtureProvider(tmp_path)
    w = Workflow(p)
    out = w.search("parent", "topic", limit=25)
    assert len(out["records"]) == 25
    assert [x[1]["page"] for x in p.calls] == [1, 2]
    assert [x[1]["num"] for x in p.calls] == [20, 20]
    p.calls = []
    w.versions("parent", "123")
    assert "q" not in p.calls[0][1] and p.calls[0][1]["cluster"] == "123"


def test_backward_direction_and_ambiguous_title(tmp_path):
    p = FixtureProvider(tmp_path)
    w = Workflow(p)
    out = w.citations("r", "W1", provider="openalex", direction="backward")
    assert out["records"][0]["title"] == "Reference"
    assert out["records"][0]["relationships"] == [
        {"seed": "W1", "direction": "backward"}
    ]
    assert w.snowball("r", ["ambiguous", "missing"])["status"] == "partial"
    assert all("cites" not in (x[1] or {}) for x in p.calls)


def test_bibtex_link_failure_keeps_metadata(tmp_path, monkeypatch):
    from litsearch.records import scholar
    from litsearch.state import Blocked

    monkeypatch.setattr("litsearch.acquisition.zotero_match", lambda r: None)

    def fail(*a, **k):
        raise Blocked("download_failed")

    monkeypatch.setattr("litsearch.acquisition.download_bytes", fail)
    p = FixtureProvider(tmp_path)
    p.request = lambda *a, **k: {
        "links": [{"title": "BibTeX", "link": "https://example.org/bib"}]
    }
    r = scholar(
        {
            "title": "Paper",
            "data_cid": "001",
            "authors": [{"name": "Researcher"}],
            "publication": "Journal, 2024",
        },
        {},
    )
    out = Workflow(p).enrich("r", [r], cite_export=True)
    assert "bibtex_export_failed_metadata_fallback" in out["records"][0]["triage_flags"]
    assert out["records"][0]["authors"] == ["Researcher"]


def test_valid_legacy_seed_and_forward_filter(tmp_path):
    p = FixtureProvider(tmp_path)
    p.request = lambda provider, run, params=None, **k: {
        "organic_results": [
            {
                "title": "Unique title",
                "data_cid": "001",
                "inline_links": {"cited_by": {"cites_id": "999"}},
            }
        ]
    }
    out = Workflow(p).snowball("r", ["Unique title"])
    assert out["status"] == "complete" and out["records"][0]["seed"] == "Unique title"
    p = FixtureProvider(tmp_path)
    Workflow(p).citations("r", "W1", provider="openalex")
    assert p.calls[0][1]["filter"] == "cites:W1"


def test_openalex_forward_pagination_keeps_page_size(tmp_path):
    p = FixtureProvider(tmp_path)

    def response(provider, run, params=None, **kwargs):
        assert params["per_page"] == 100
        return {
            "results": [
                {
                    "id": f'https://openalex.org/W{(params["page"]-1)*100+i}',
                    "title": f"Paper {i}",
                }
                for i in range(100)
            ]
        }

    p.request = response
    out = Workflow(p).citations("r", "W999", provider="openalex", limit=150)
    assert len(out["records"]) == 150
    assert len({r["identifiers"]["openalex"] for r in out["records"]}) == 150
