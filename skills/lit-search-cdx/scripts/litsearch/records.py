"""Provider records, evidence and identity normalization, independent of HTTP."""

import copy
import datetime as dt
import re
from urllib.parse import unquote
from .state import digest


def title_key(s):
    return re.sub(r"[^\w]+", "", str(s).casefold())


def doi(s):
    return re.sub(
        r"^(?:https?://(?:dx\.)?doi.org/|doi:\s*)", "", str(s or "").strip(), flags=re.I
    ).lower()


def arxiv(s):
    m = re.search(
        r"(?:arxiv(?:\.org/(?:abs|pdf)/|:))((?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7}))(?:v\d+)?",
        str(s),
        re.I,
    )
    return m[1].lower() if m else None


def base(title, provider, identifiers, query):
    return {
        "id": provider + ":" + digest(identifiers or [title, query])[:20],
        "title": title or "",
        "authors": [],
        "year": None,
        "venue": None,
        "doi": None,
        "arxiv": None,
        "abstract": None,
        "snippet": None,
        "url": None,
        "identifiers": identifiers,
        "citation_counts": {},
        "pdf_locations": [],
        "provenance": [
            {
                "provider": provider,
                "request": query,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
        ],
        "triage_flags": [],
    }


def scholar(raw, query, retrieved_at=None):
    links = raw.get("inline_links") or {}
    cited = links.get("cited_by") or {}
    versions = links.get("versions") or {}
    ids = {
        k: str(v)
        for k, v in {
            "scholar_cid": raw.get("data_cid"),
            "scholar_cites": cited.get("cites_id"),
            "scholar_cluster": versions.get("cluster_id"),
        }.items()
        if v is not None
    }
    r = base(raw.get("title"), "scholar", ids, query)
    if retrieved_at:
        r["provenance"][0]["retrieved_at"] = retrieved_at
    r.update(
        authors=[
            a.get("name", "") if isinstance(a, dict) else a
            for a in raw.get("authors", [])
        ],
        snippet=raw.get("snippet"),
        url=raw.get("link"),
    )
    r["arxiv"] = arxiv(r["url"])
    r["doi"] = doi(raw.get("doi")) or None
    if not r["doi"] and "doi.org/" in (r["url"] or ""):
        r["doi"] = doi(r["url"])
    pub = raw.get("publication", "")
    year = re.search(r"\b(19|20)\d{2}\b", pub)
    r["year"] = int(year[0]) if year else None
    r["publication_text"] = pub
    author_text = pub.split(" - ", 1)[0]
    if "…" in author_text or "..." in author_text:
        r["triage_flags"].append("incomplete_author_list")
    r["citation_counts"] = {"scholar": cited.get("total", 0)}
    resource = raw.get("resource") or {}
    if resource.get("format", "").upper() == "PDF" and resource.get("link"):
        r["pdf_locations"].append(
            {"url": resource["link"], "source": "direct", "version": None}
        )
    return r


def openalex(raw, query, retrieved_at=None):
    ids = {k: v for k, v in (raw.get("ids") or {}).items() if v}
    if raw.get("id"):
        ids["openalex"] = raw["id"].rsplit("/", 1)[-1]
    r = base(raw.get("display_name") or raw.get("title"), "openalex", ids, query)
    if retrieved_at or raw.get("_litsearch_retrieved_at"):
        r["provenance"][0]["retrieved_at"] = (
            retrieved_at or raw["_litsearch_retrieved_at"]
        )
    r.update(
        doi=doi(raw.get("doi")) or None,
        year=raw.get("publication_year"),
        url=raw.get("doi") or raw.get("id"),
        authors=[
            a["author"]["display_name"]
            for a in raw.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ],
    )
    r["metadata_preference"] = "openalex"
    r["venue"] = ((raw.get("primary_location") or {}).get("source") or {}).get(
        "display_name"
    )
    index = raw.get("abstract_inverted_index")
    if index:
        r["abstract"] = " ".join(
            w for _, w in sorted((i, w) for w, pos in index.items() for i in pos)
        )
    r["citation_counts"] = {"openalex": raw.get("cited_by_count", 0)}
    r["referenced_works"] = [
        x.rsplit("/", 1)[-1] for x in raw.get("referenced_works", [])
    ]
    for loc in raw.get("locations") or []:
        r["arxiv"] = (
            r["arxiv"]
            or arxiv(loc.get("landing_page_url"))
            or arxiv(loc.get("pdf_url"))
        )
        if loc.get("pdf_url"):
            r["pdf_locations"].append(
                {
                    "url": loc["pdf_url"],
                    "source": "direct",
                    "version": loc.get("version"),
                }
            )
    content = raw.get("content_urls") or {}
    if content.get("pdf"):
        r["pdf_locations"].append(
            {"url": content["pdf"], "source": "openalex_cache", "version": None}
        )
    return r


def same(a, b):
    return bool(
        (a.get("doi") and doi(a["doi"]) == doi(b.get("doi")))
        or (a.get("arxiv") and a["arxiv"] == b.get("arxiv"))
    )


def merge(records):
    from difflib import SequenceMatcher

    result = []
    for item in records:
        r = copy.deepcopy(item)
        exact = [x for x in result if same(x, r) or x["id"] == r["id"]]
        if exact:
            target = exact[0]
            for source in [r] + exact[1:]:
                for key in (
                    "authors",
                    "year",
                    "venue",
                    "abstract",
                    "doi",
                    "arxiv",
                    "url",
                ):
                    if not target.get(key) and source.get(key):
                        target[key] = source[key]
                for key in (
                    "provenance",
                    "pdf_locations",
                    "referenced_works",
                    "relationships",
                    "triage_flags",
                    "aliases",
                ):
                    for value in source.get(key, []):
                        if value not in target.setdefault(key, []):
                            target[key].append(value)
                if (
                    source.get("metadata_preference") == "openalex"
                    and target.get("metadata_preference") != "zotero"
                    and source.get("authors")
                ):
                    target["authors"] = source["authors"]
                    target["metadata_preference"] = "openalex"
                    target["triage_flags"] = [
                        f
                        for f in target.get("triage_flags", [])
                        if f != "incomplete_author_list"
                    ]
                target.setdefault("identifier_history", [])
                for ids in [
                    target.get("identifiers", {}),
                    source.get("identifiers", {}),
                ] + source.get("identifier_history", []):
                    if ids not in target["identifier_history"]:
                        target["identifier_history"].append(copy.deepcopy(ids))
                target.setdefault("identifiers", {}).update(
                    source.get("identifiers", {})
                )
                target.setdefault("citation_counts", {}).update(
                    source.get("citation_counts", {})
                )
                if source["id"] != target["id"] and source[
                    "id"
                ] not in target.setdefault("aliases", []):
                    target["aliases"].append(source["id"])
            for old in exact[1:]:
                result.remove(old)
        else:
            for x in result:
                a, b = title_key(x["title"]), title_key(r["title"])
                if a and b and SequenceMatcher(None, a, b).ratio() >= 0.8:
                    for obj, other in [(x, r), (r, x)]:
                        flag = "possible_duplicate:" + other["id"]
                        if flag not in obj.setdefault("triage_flags", []):
                            obj["triage_flags"].append(flag)
            result.append(r)
    return result


def bibtex(r, attachment=None):
    author_text = r.get("publication_text", "").split(" - ", 1)[0]
    if r.get("metadata_preference") not in ("openalex", "zotero") and (
        "incomplete_author_list" in r.get("triage_flags", [])
        or "…" in author_text
        or "..." in author_text
    ):
        return None
    if not r.get("title") or not r.get("authors") or not r.get("year"):
        return None
    key = (
        r.get("citation_key")
        or re.sub(r"\W", "", r["authors"][0].split()[-1])
        + str(r["year"])
        + digest(r["id"])[:8]
    )

    def escape(v):
        return (
            str(v)
            .replace("\\", r"\textbackslash{}")
            .replace("{", r"\{")
            .replace("}", r"\}")
            .replace("&", r"\&")
            .replace("%", r"\%")
            .replace("_", r"\_")
            .replace("#", r"\#")
        )

    fields = {
        "title": r["title"],
        "author": " and ".join(r["authors"]),
        "year": r["year"],
        "journal": r.get("venue"),
        "doi": r.get("doi"),
        "url": r.get("url"),
    }
    text = "@article{" + re.sub(r"[^a-zA-Z0-9_.:-]", "", key) + ",\n"
    text += "".join(
        "  " + k + " = {" + escape(v) + "},\n" for k, v in fields.items() if v
    )
    if attachment:
        text += "  file = {" + attachment + "},\n"
    return text + "}\n"
