"""Search operations return recoverable envelopes with normalized records."""

import copy
import re
from urllib.parse import quote
from .state import Blocked
from .records import scholar, openalex, merge, title_key, same


class Workflow:
    def __init__(self, providers):
        self.p = providers

    def envelope(self, run, records, remaining=None, completed=None):
        remaining = remaining or []
        return {
            "schema_version": 1,
            "run_id": run,
            "status": (
                ("partial" if records else "blocked") if remaining else "complete"
            ),
            "records": merge(records),
            "remaining_work": remaining,
            "completed": completed or [],
            "usage": self.p.state.usage(run),
            "credential_sources": self.p.sources,
            "account": self.p.accounts,
        }

    def search(self, run, query, provider="scholar", limit=20, refresh=False, mode="q"):
        if not 1 <= limit <= 10000:
            raise ValueError("limit must be 1..10000")
        records = []
        remaining = []
        completed = []
        page = 1
        while len(records) < limit:
            num = 20
            params = (
                {"engine": "google_scholar", mode: query, "page": page, "num": num}
                if provider == "scholar"
                else {"search": query, "page": page, "per_page": num}
            )
            try:
                raw = self.p.request(
                    "searchapi" if provider == "scholar" else "openalex",
                    run,
                    params,
                    refresh=refresh,
                )
            except Blocked as e:
                remaining.append(
                    {
                        "operation": "search",
                        "query": query,
                        "provider": provider,
                        "mode": mode,
                        "page": page,
                        "reason": e.code,
                        **e.details,
                    }
                )
                break
            rows = raw.get(
                "organic_results" if provider == "scholar" else "results", []
            )
            convert = scholar if provider == "scholar" else openalex
            records.extend(
                convert(
                    r,
                    params,
                    raw.get("_litsearch_retrieved_at")
                    or raw.get("search_metadata", {}).get("created_at"),
                )
                for r in rows[: min(num, limit - len(records))]
            )
            completed.append({"query": query, "page": page, "provider": provider})
            if len(rows) < num:
                break
            page += 1
        return self.envelope(run, records, remaining, completed)

    def versions(self, run, seed, limit=20, refresh=False):
        if not re.fullmatch(r"\d+", seed):
            return self.envelope(
                run, [], [{"seed": seed, "reason": "scholar_cluster_id_required"}]
            )
        out = self.search(run, seed, limit=limit, refresh=refresh, mode="cluster")
        for r in out["records"]:
            r["relationships"] = [{"seed": seed, "direction": "versions"}]
        return out

    def citations(
        self,
        run,
        seed,
        provider="scholar",
        direction="forward",
        limit=20,
        refresh=False,
    ):
        if not 1 <= limit <= 10000:
            raise ValueError("limit must be 1..10000")
        if provider == "scholar":
            if direction != "forward" or not re.fullmatch(r"\d+", seed):
                return self.envelope(
                    run,
                    [],
                    [
                        {
                            "seed": seed,
                            "reason": "use_openalex_for_backward_or_supply_scholar_cites_id",
                        }
                    ],
                )
            out = self.search(run, seed, limit=limit, refresh=refresh, mode="cites")
        else:
            records = []
            remaining = []
            completed = []
            try:
                work = seed.rsplit("/", 1)[-1] if "openalex.org/" in seed else seed
                if not re.fullmatch(r"W\d+", work):
                    raw = self.p.request(
                        "openalex",
                        run,
                        path="works/" + quote(seed, safe=""),
                        refresh=refresh,
                    )
                    work = raw["id"].rsplit("/", 1)[-1]
                if direction == "backward":
                    raw = self.p.request(
                        "openalex", run, path="works/" + work, refresh=refresh
                    )
                    refs = raw.get("referenced_works", [])[:limit]
                    for ref in refs:
                        ident = ref.rsplit("/", 1)[-1]
                        try:
                            records.append(
                                openalex(
                                    self.p.request(
                                        "openalex",
                                        run,
                                        path="works/" + ident,
                                        refresh=refresh,
                                    ),
                                    {"seed": seed, "direction": direction},
                                )
                            )
                            completed.append(ident)
                        except Blocked as e:
                            remaining.append(
                                {"seed": seed, "reference": ident, "reason": e.code}
                            )
                else:
                    page = 1
                    while len(records) < limit:
                        n = 100
                        params = {
                            "filter": "cites:" + work,
                            "per_page": n,
                            "page": page,
                        }
                        raw = self.p.request("openalex", run, params, refresh=refresh)
                        rows = raw.get("results", [])
                        records.extend(
                            openalex(r, params, raw.get("_litsearch_retrieved_at"))
                            for r in rows[: min(n, limit - len(records))]
                        )
                        completed.append({"page": page, "seed": seed})
                        if len(rows) < n:
                            break
                        page += 1
            except (Blocked, KeyError) as e:
                remaining.append(
                    {
                        "seed": seed,
                        "direction": direction,
                        "reason": (
                            e.code if isinstance(e, Blocked) else "missing_identifier"
                        ),
                    }
                )
            out = self.envelope(run, records, remaining, completed)
        for r in out["records"]:
            r["relationships"] = [{"seed": seed, "direction": direction}]
        return out

    def snowball(self, run, titles, limit=10):
        records = []
        remaining = []
        completed = []
        for title in titles:
            found = self.search(run, title, limit=20)
            matches = [
                r for r in found["records"] if title_key(r["title"]) == title_key(title)
            ]
            if (
                found["remaining_work"]
                or len(matches) != 1
                or not matches[0]["identifiers"].get("scholar_cites")
            ):
                remaining.append(
                    {
                        "seed": title,
                        "reason": (
                            "ambiguous_seed" if len(matches) > 1 else "unresolved_seed"
                        ),
                        "details": found["remaining_work"],
                    }
                )
                continue
            out = self.citations(
                run, matches[0]["identifiers"]["scholar_cites"], limit=limit
            )
            for r in out["records"]:
                r["seed"] = title
            records += out["records"]
            remaining += out["remaining_work"]
            completed += out["completed"]
        result = self.envelope(run, records, remaining, completed)
        if remaining:
            result["status"] = "partial"
        return result

    def enrich(self, run, records, refresh=False, cite_export=False):
        from .acquisition import zotero_match, download_bytes

        output = []
        remaining = []
        for candidate in records:
            r = copy.deepcopy(candidate)
            match = zotero_match(r)
            if match:
                r.update(match)
            if r.get("doi") or r.get("identifiers", {}).get("openalex"):
                ident = (
                    r.get("identifiers", {}).get("openalex")
                    or "https://doi.org/" + r["doi"]
                )
                try:
                    raw = self.p.request(
                        "openalex",
                        run,
                        path="works/" + quote(ident, safe=""),
                        refresh=refresh,
                    )
                    enriched = openalex(raw, {"lookup": ident})
                    if same(r, enriched) or r.get("identifiers", {}).get(
                        "openalex"
                    ) == enriched["identifiers"].get("openalex"):
                        r = merge([r, enriched])[0]
                    else:
                        remaining.append(
                            {"id": r["id"], "reason": "metadata_identity_mismatch"}
                        )
                except Blocked as e:
                    remaining.append({"id": r["id"], "reason": e.code})
            elif not match:
                remaining.append(
                    {
                        "id": r["id"],
                        "reason": "identifier_required_for_verified_enrichment",
                    }
                )
            if cite_export and r.get("identifiers", {}).get("scholar_cid"):
                try:
                    data = self.p.request(
                        "searchapi",
                        run,
                        {
                            "engine": "google_scholar_cite",
                            "data_cid": r["identifiers"]["scholar_cid"],
                        },
                        refresh=refresh,
                    )
                    link = next(
                        x["link"]
                        for x in data.get("links", [])
                        if x.get("title") == "BibTeX"
                    )
                    text = download_bytes(link, max_bytes=100000)[0].decode()
                    if not text.lstrip().startswith("@"):
                        raise ValueError()
                    # Reference evidence only. Bundle uses verified metadata.
                    r["scholar_bibtex"] = text
                except (Blocked, ValueError, StopIteration, UnicodeError):
                    r.setdefault("triage_flags", []).append(
                        "bibtex_export_failed_metadata_fallback"
                    )
            output.append(r)
        return self.envelope(run, output, remaining, [r["id"] for r in output])


def report(envelope):
    lines = [
        "# Literature search results",
        "",
        "Status: " + envelope["status"],
        "Run: " + envelope["run_id"],
        "",
    ]
    for r in envelope["records"]:
        lines += [
            "## " + r["title"],
            "",
            "ID: " + r["id"],
            "Authors: " + ", ".join(r.get("authors", [])),
            "Year: " + str(r.get("year") or "unknown"),
            "DOI: " + str(r.get("doi") or "unresolved"),
            "",
        ]
        if r.get("zotero_import"):
            lines += ["Zotero import: " + str(r["zotero_import"]), ""]
        if r.get("abstract"):
            lines += ["Abstract: " + r["abstract"], ""]
        if r.get("snippet"):
            lines += ["Search snippet: " + r["snippet"], ""]
    if envelope.get("bundle"):
        lines += [
            "Bundle: [" + envelope["bundle"] + "](" + envelope["bundle"] + ")",
            "",
        ]
    lines += ["## Remaining work", ""] + [
        str(x) for x in envelope.get("remaining_work", [])
    ]
    return "\n".join(lines) + "\n"
