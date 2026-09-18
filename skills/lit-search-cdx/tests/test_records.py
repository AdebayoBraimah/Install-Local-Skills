from litsearch.records import scholar, openalex, merge


def test_scholar_snippet_ids_and_exact_dedup():
    a = scholar(
        {
            "title": "A",
            "data_cid": "001",
            "link": "https://arxiv.org/abs/1706.03762v2",
            "snippet": "snippet",
            "inline_links": {"cited_by": {"cites_id": "99999999999999999", "total": 4}},
        },
        {"q": "x", "page": 1},
    )
    assert a["abstract"] is None and a["snippet"] == "snippet"
    assert a["identifiers"]["scholar_cites"] == "99999999999999999"
    b = scholar(
        {"title": "A", "data_cid": "002", "link": "https://arxiv.org/pdf/1706.03762v3"},
        {"q": "y", "page": 2},
    )
    out = merge([a, b])
    assert len(out) == 1 and len(out[0]["provenance"]) == 2
    c = scholar({"title": "A", "data_cid": "003"}, {})
    assert len(merge([a, c])) == 2


def test_openalex_abstract_and_relationships():
    a = openalex(
        {
            "id": "https://openalex.org/W1",
            "display_name": "A",
            "doi": "https://doi.org/10.1/XYZ",
            "abstract_inverted_index": {"world": [1], "Hello": [0]},
            "referenced_works": ["https://openalex.org/W2"],
        },
        {},
    )
    assert a["abstract"] == "Hello world"
    assert a["referenced_works"] == ["W2"]
    assert (
        openalex({"id": "https://openalex.org/W2", "display_name": "B"}, {})["abstract"]
        is None
    )


def test_enrichment_retains_references_and_transitive_identity():
    a = scholar({"title": "A", "doi": "10.1234/x", "data_cid": "a"}, {})
    b = scholar(
        {"title": "A", "data_cid": "b", "link": "https://arxiv.org/abs/1234.12345"}, {}
    )
    c = openalex(
        {
            "id": "https://openalex.org/W1",
            "title": "A",
            "doi": "10.1234/x",
            "referenced_works": ["https://openalex.org/W2"],
            "locations": [{"landing_page_url": "https://arxiv.org/abs/1234.12345"}],
        },
        {},
    )
    out = merge([a, b, c])
    assert len(out) == 1
    assert out[0]["referenced_works"] == ["W2"]


def test_truncated_scholar_authors_require_enrichment_before_import():
    from litsearch.records import bibtex

    a = scholar(
        {
            "title": "Paper",
            "data_cid": "1",
            "authors": [{"name": "A Author"}],
            "publication": "A Author… - Journal, 2024",
        },
        {},
    )
    assert bibtex(a) is None
    b = openalex(
        {
            "id": "https://openalex.org/W1",
            "title": "Paper",
            "doi": "10.1234/x",
            "publication_year": 2024,
            "authorships": [
                {"author": {"display_name": "A Author"}},
                {"author": {"display_name": "B Author"}},
            ],
        },
        {},
    )
    a["doi"] = "10.1234/x"
    out = merge([a, b])[0]
    assert out["authors"] == ["A Author", "B Author"] and bibtex(out)
