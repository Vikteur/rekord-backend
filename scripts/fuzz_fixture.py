"""Record rapidfuzz's exact numbers, so a Java port can be checked against them.

The matcher's thresholds are calibrated to rapidfuzz's output, and the obvious
Java equivalent (a difflib-based port) returns different values for the same
strings. This dumps enough pairs — real ones from the library, plus the edge
cases that separate one implementation from another — to tell the two apart.

    REKORD_DB=/abs/snapshot.db python -m scripts.fuzz_fixture --out fuzz-fixture.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

if not os.environ.get("REKORD_DB"):
    sys.exit("Set REKORD_DB to a snapshot; this reads real titles.")

from rapidfuzz import fuzz  # noqa: E402

from server import db  # noqa: E402
from server.matcher.normalize import normalize  # noqa: E402

SEED = 20260829

# The cases where implementations actually diverge, rather than where they
# obviously agree.
EDGE_PAIRS = [
    ("", ""),
    ("", "anything"),
    ("a", "a"),
    ("a", "b"),
    ("abc", "abcd"),
    # Order-insensitivity: the difference between sort and set semantics.
    ("anthem", "other anthem of ours"),
    ("one two three", "three two one"),
    ("a b c", "c b a"),
    # Subset on one side only, which is where token_set short-circuits.
    ("fleetwood mac", "fleetwood mac rumours"),
    ("dreams", "dreams fleetwood mac"),
    # Repeated tokens: sets collapse them, sorts do not.
    ("la la la", "la"),
    ("the the", "the"),
    # Transpositions and drops, where LCS and greedy block matching disagree.
    ("substitution", "substitution"),
    ("purple disco machine", "purple diso machine"),
    ("aabbcc", "ccbbaa"),
    ("abcdef", "badcfe"),
    # Long-ish, so the block heuristic has room to differ from a true LCS.
    ("dont you forget about me simple minds", "simple minds dont you forget about me"),
    ("mr brightside the killers", "the killers mr brightside 2004 remaster"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fuzz-fixture.json")
    ap.add_argument("--pairs", type=int, default=400)
    args = ap.parse_args()

    db.init()
    libraries = db.list_libraries()
    if not libraries:
        raise SystemExit("No libraries in this database.")
    tracks = db.library_tracks(libraries[0].id)

    rng = random.Random(SEED)
    usable = sorted(
        (t for t in tracks if t.artist and t.title),
        key=lambda t: t.id,
    )

    pairs: list[tuple[str, str]] = list(EDGE_PAIRS)

    # Real pairs, normalized the way the matcher normalizes before scoring.
    for _ in range(args.pairs):
        a, b = rng.sample(usable, 2)
        pairs.append((normalize(a.title), normalize(b.title)))
        pairs.append((normalize(a.artist), normalize(b.artist)))
    # And each title against itself with a small perturbation, which is where
    # near-misses live.
    for track in rng.sample(usable, min(100, len(usable))):
        title = normalize(track.title)
        if len(title) > 4:
            cut = len(title) // 2
            pairs.append((title, title[:cut] + title[cut + 1 :]))
            pairs.append((title, title + " remix"))

    seen = set()
    cases = []
    for a, b in pairs:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        cases.append(
            {
                "a": a,
                "b": b,
                "ratio": fuzz.ratio(a, b),
                "token_sort_ratio": fuzz.token_sort_ratio(a, b),
                "token_set_ratio": fuzz.token_set_ratio(a, b),
            }
        )

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"note": "rapidfuzz output; the Java port must reproduce it.",
                   "cases": cases}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"{len(cases)} pairs -> {args.out}")


if __name__ == "__main__":
    main()
