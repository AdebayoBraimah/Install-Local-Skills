#!/usr/bin/env python
"""Google Scholar search via scholarly for the lit-survey pipeline.

Usage:
    python scholarly_search.py "query string" [max_results]

Output: JSON array of paper metadata to stdout.

Rate limiting: 7-second delay between scholarly.fill() calls to avoid
Google Scholar blocking. Cap at max_results (default 15).
"""

import json
import sys
import time

from scholarly import scholarly


def search(query: str, max_results: int = 15) -> list[dict]:
    """Search Google Scholar and return structured metadata."""
    results = []
    for i, pub in enumerate(scholarly.search_pubs(query)):
        if i >= max_results:
            break
        try:
            pub = scholarly.fill(pub)
            results.append(
                {
                    "title": pub["bib"].get("title", ""),
                    "authors": pub["bib"].get("author", ""),
                    "year": pub["bib"].get("pub_year", ""),
                    "venue": pub["bib"].get("venue", ""),
                    "abstract": pub["bib"].get("abstract", "")[:500],
                    "citations": pub.get("num_citations", 0),
                    "url": pub.get("pub_url", ""),
                    "eprint": pub.get("eprint_url", ""),
                }
            )
        except Exception as e:
            results.append(
                {
                    "error": str(e),
                    "title": pub["bib"].get("title", "unknown"),
                }
            )
        time.sleep(7)
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: scholarly_search.py 'query' [max_results]", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    results = search(query, max_results)
    print(json.dumps(results, indent=2))
