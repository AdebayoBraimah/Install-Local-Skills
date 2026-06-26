#!/usr/bin/env python
"""Citation graph traversal via scholarly.citedby() for snowball searching.

Usage:
    python scholarly_snowball.py seeds.json [max_citing_per_seed]

Input: JSON file with array of seed paper titles:
    ["Paper title 1", "Paper title 2", ...]

Output: JSON array of citing paper metadata with seed attribution to stdout.

Rate limiting: 10-second delay between citedby() results, 15-second delay
between seeds. citedby() is the most rate-limited scholarly function.
"""

import json
import sys
import time

from scholarly import scholarly


def snowball(seed_titles: list[str], max_per_seed: int = 10) -> list[dict]:
    """Find papers citing the given seed papers."""
    all_citing = []

    for title in seed_titles:
        try:
            results = scholarly.search_pubs(title)
            pub = next(results, None)
            if not pub:
                all_citing.append({"seed": title, "error": "not found"})
                continue

            pub = scholarly.fill(pub)
            for i, citing in enumerate(scholarly.citedby(pub)):
                if i >= max_per_seed:
                    break
                all_citing.append(
                    {
                        "seed": title,
                        "title": citing["bib"].get("title", ""),
                        "authors": citing["bib"].get("author", ""),
                        "year": citing["bib"].get("pub_year", ""),
                        "venue": citing["bib"].get("venue", ""),
                        "citations": citing.get("num_citations", 0),
                        "url": citing.get("pub_url", ""),
                    }
                )
                time.sleep(10)
        except Exception as e:
            all_citing.append({"seed": title, "error": str(e)})
        time.sleep(15)

    return all_citing


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: scholarly_snowball.py seeds.json [max_citing_per_seed]",
            file=sys.stderr,
        )
        sys.exit(1)

    seeds_path = sys.argv[1]
    max_per_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    with open(seeds_path) as f:
        seed_titles = json.load(f)

    results = snowball(seed_titles, max_per_seed)
    print(json.dumps(results, indent=2))
