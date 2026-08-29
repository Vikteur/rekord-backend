"""Capture the matcher's behaviour as a fixed oracle, for porting it to Java.

The Java rewrite has to reproduce `server/matcher/` — but the thresholds in
`score.py` are calibrated against rapidfuzz's exact numbers, and no Java
library returns the same ones. `docs/business-analysis.md` §11.1 admits the
matcher's accuracy has never actually been measured, so there is nothing
today that would notice a port getting it wrong.

This writes that missing baseline: a set of queries run through the real
matcher against a real library, with everything the matcher decided recorded
verbatim — bucket, auto-pick, and every candidate's score and facet
breakdown. The port is correct when it reproduces this file.

It records what Python *does*, not what is *right*. A wrong-but-recorded
answer still belongs here: the question a port has to answer is "did I change
the behaviour", which is separate from "is the behaviour good". Measuring
quality needs hand-labelled truth and is a different exercise.

    REKORD_DB=/tmp/snapshot.db python -m scripts.golden_set --out golden-set.json

Point REKORD_DB at a *snapshot*, never at a live database — the matcher
itself only reads, but opening it runs schema migrations, which write.
Take the snapshot with SQLite's backup API rather than copying the file: a
plain `cp` of a database in WAL mode can tear.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from dataclasses import dataclass, field

if not os.environ.get("REKORD_DB"):
    sys.exit("Refusing to run against the default database. Set REKORD_DB to a snapshot.")

from server import db  # noqa: E402  (import after REKORD_DB is checked)
from server.library import LIBRARIES  # noqa: E402
from server.matcher.index import LibraryIndex  # noqa: E402
from server.matcher.match import match_one  # noqa: E402
from server.matcher.versions import extract_version  # noqa: E402
from server.models import LibraryTrack, PlaylistTrackInput  # noqa: E402

SEED = 20260829  # fixed: the same library must always yield the same cases


@dataclass
class Case:
    """One query, and why it is interesting."""

    family: str
    note: str
    artist: str
    title: str
    duration_sec: float | None = None
    # The track this query was derived from, when it came from the library.
    # Recorded for diagnosis only — it is NOT an assertion that the matcher
    # should return it. Some families deliberately make that unlikely.
    derived_from: str | None = None
    tags: list[str] = field(default_factory=list)


# --- query construction -----------------------------------------------------
#
# Real Spotify playlists aren't available here, so queries are derived from the
# library itself and then bent in the ways a streaming tracklist actually
# differs from a DJ's files: version suffixes present on one side and not the
# other, featured artists moved in and out of the title, punctuation, typos.

_LETTER = re.compile(r"[a-z]", re.I)


def _swap_two_letters(text: str, rng: random.Random) -> str:
    """Transpose an adjacent pair — the most common real typing error."""
    positions = [m.start() for m in _LETTER.finditer(text) if m.start() + 1 < len(text)]
    if not positions:
        return text
    i = rng.choice(positions)
    return text[:i] + text[i + 1] + text[i] + text[i + 2:]


def _drop_a_letter(text: str, rng: random.Random) -> str:
    positions = [m.start() for m in _LETTER.finditer(text)]
    if not positions:
        return text
    i = rng.choice(positions)
    return text[:i] + text[i + 1:]


def _usable(track: LibraryTrack) -> bool:
    """Tracks with real artist+title tags, long enough to be a song."""
    return bool(
        track.artist
        and track.title
        and track.tag_source != "filename"
        and (track.duration_sec or 0) > 30
    )


def build_cases(tracks: list[LibraryTrack], per_family: int) -> list[Case]:
    rng = random.Random(SEED)
    pool = sorted((t for t in tracks if _usable(t)), key=lambda t: t.id)
    if len(pool) < per_family:
        raise SystemExit(f"Library too small: {len(pool)} usable tracks.")

    def sample(n: int) -> list[LibraryTrack]:
        return rng.sample(pool, min(n, len(pool)))

    def sample_from(subset: list[LibraryTrack], n: int) -> list[LibraryTrack]:
        return rng.sample(subset, min(n, len(subset))) if subset else []

    cases: list[Case] = []

    # 1. Verbatim tags. The floor: if these regress, something is badly wrong.
    for t in sample(per_family):
        cases.append(Case("exact", "artist and title straight off the file",
                          t.artist, t.title, t.duration_sec, t.id))

    # 2. Version suffix stripped. Spotify lists "Song"; the file is
    #    "Song (Extended Mix)". The most common real-world mismatch.
    stripped = [t for t in pool if extract_version(t.title).descriptors]
    for t in sample_from(stripped, per_family):
        cases.append(Case("core_only", "file has a version suffix, query does not",
                          t.artist, extract_version(t.title).core_title,
                          t.duration_sec, t.id))

    # 3. The mirror image: the query asks for a version the file does not name.
    #    version_score should fall and block the auto-pick.
    plain = [t for t in pool if not extract_version(t.title).descriptors]
    for t in sample_from(plain, per_family):
        cases.append(Case("added_version", "query asks for a version the file does not name",
                          t.artist, f"{t.title} - Radio Edit", t.duration_sec, t.id))

    # 4. Typos. Exercises the fuzzy scorer rather than the token index.
    for i, t in enumerate(sample(per_family)):
        bent = (_swap_two_letters if i % 2 else _drop_a_letter)(t.title, rng)
        if bent != t.title:
            cases.append(Case("typo", "one mistyped character in the title",
                              t.artist, bent, t.duration_sec, t.id))

    # 5. No artist — pasted tracklists often lose it. Drops the artist facet
    #    and leans on title alone.
    for t in sample(per_family):
        cases.append(Case("no_artist", "title only, artist empty", "", t.title,
                          t.duration_sec, t.id))

    # 6. "&" vs "and" — normalize() folds these; this proves the port's does.
    amp = [t for t in pool if "&" in (t.artist or "") or "&" in t.title]
    for t in sample_from(amp, per_family):
        cases.append(Case("ampersand", "ampersand spelled out",
                          (t.artist or "").replace("&", "and"),
                          t.title.replace("&", "and"), t.duration_sec, t.id))

    # 7. Featured artist moved into the title, as Spotify writes it.
    for t in sample(max(1, per_family // 2)):
        cases.append(Case("feat_inline", "featured artist folded into the title",
                          "", f"{t.title} (feat. {t.artist})", t.duration_sec, t.id))

    # 8. Case and punctuation noise.
    for t in sample(max(1, per_family // 2)):
        cases.append(Case("case_punct", "uppercased, punctuation stripped",
                          (t.artist or "").upper(),
                          re.sub(r"[^\w\s]", "", t.title).upper(), t.duration_sec, t.id))

    # 9. Wrong duration. Isolates duration_score: everything else matches, so a
    #    port that gets the curve wrong shows up here and nowhere else.
    for t in sample(max(1, per_family // 2)):
        if t.duration_sec:
            cases.append(Case("duration_off", "correct song, duration 45s out",
                              t.artist, t.title, t.duration_sec + 45, t.id))

    # 10. Songs that are not in the library at all: the unmatched bucket, and a
    #     check that nothing scores high enough to be auto-picked.
    for artist, title in [
        ("Nonexistent Artist Qzx", "A Song That Is Not Here"),
        ("Fictional Band 9981", "Untitled Placeholder"),
        ("Zzzz Quorum", "Absolutely Nothing Like This"),
        ("Placeholder Collective", "Song Number Four Four Four"),
        ("Imaginary Duo", "Nowhere To Be Found"),
    ]:
        cases.append(Case("unowned", "not in the library", artist, title, 210.0))

    return cases


def preference_cases(library_id: int) -> list[Case]:
    """Real remembered choices: a human already resolved these ambiguities.

    The highest-value cases in the set, because a preference must override
    scoring entirely — including re-scoring a track the index never surfaced.
    """
    return [
        Case("preference", "a version the DJ chose before",
             pref.artist, pref.title, None, pref.track_id,
             tags=["expects_from_preference"])
        for pref in db.list_preferences(library_id)
    ]


def playlist_cases(library_id: int, limit: int) -> list[Case]:
    """Tracks in an imported rekordbox playlist, so PLAYLIST_BONUS applies.

    The bonus must reorder candidates without changing the bucket — it is
    added for ranking only, and bucketing reads the raw score.
    """
    membership = db.playlist_membership(library_id)
    by_id = {t.id: t for t in db.library_tracks(library_id)}
    cases = []
    for track_id in sorted(membership)[:limit]:
        t = by_id.get(track_id)
        if t and _usable(t):
            cases.append(Case("playlist_member", "in an imported rekordbox playlist",
                              t.artist, t.title, t.duration_sec, t.id,
                              tags=["has_playlist_bonus"]))
    return cases


# --- capture ----------------------------------------------------------------

def _round(value: float | None, places: int = 6) -> float | None:
    """Scores are compared numerically, so pin the precision explicitly.

    6 places is far tighter than any threshold in score.py (the closest pair is
    AUTO_MARGIN at 0.10), so this records real differences without making float
    noise look like one.
    """
    return None if value is None else round(float(value), places)


def capture(case: Case, index: LibraryIndex, prefs, membership) -> dict:
    result = match_one(
        PlaylistTrackInput(index=0, artist=case.artist, title=case.title,
                           duration_sec=case.duration_sec),
        index, prefs, membership,
    )
    return {
        "family": case.family,
        "note": case.note,
        "tags": case.tags,
        "derived_from": case.derived_from,
        "query": {"artist": case.artist, "title": case.title,
                  "duration_sec": case.duration_sec},
        "expected": {
            "bucket": result.bucket,
            "auto_selected_id": result.auto_selected_id,
            "from_preference": result.from_preference,
            "input_version": {
                "descriptors": result.input_version.descriptors,
                "remixer": result.input_version.remixer,
            },
            "candidate_count": len(result.candidates),
            "candidates": [
                {
                    "track_id": c.track.id,
                    "artist": c.track.artist,
                    "title": c.track.title,
                    "score": _round(c.score),
                    "parts": {k: _round(v) for k, v in sorted(c.parts.items())},
                    "version": {"descriptors": c.version.descriptors,
                                "remixer": c.version.remixer},
                    "duration_delta_sec": _round(c.duration_delta_sec, 3),
                    "playlists": sorted(c.playlists),
                }
                for c in result.candidates
            ],
        },
    }


def _thresholds() -> dict:
    """Pinned so a threshold edit shows up as a golden-set diff, not a silent
    behaviour change that the recorded scores happen to still satisfy."""
    from server.matcher import score as s
    return {
        "REPORT_THRESHOLD": s.REPORT_THRESHOLD, "STRONG_THRESHOLD": s.STRONG_THRESHOLD,
        "AUTO_SCORE": s.AUTO_SCORE, "AUTO_MARGIN": s.AUTO_MARGIN,
        "AUTO_MIN_VERSION": s.AUTO_MIN_VERSION, "AUTO_MIN_DURATION": s.AUTO_MIN_DURATION,
        "MAX_CANDIDATES": s.MAX_CANDIDATES,
        "WEIGHT_TITLE": s.WEIGHT_TITLE, "WEIGHT_ARTIST": s.WEIGHT_ARTIST,
        "WEIGHT_COMBINED": s.WEIGHT_COMBINED, "WEIGHT_VERSION": s.WEIGHT_VERSION,
        "WEIGHT_DURATION": s.WEIGHT_DURATION,
        "PLAYLIST_BONUS": s.PLAYLIST_BONUS, "PLAYLIST_BONUS_CAP": s.PLAYLIST_BONUS_CAP,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Capture matcher behaviour as a golden set.")
    ap.add_argument("--out", default="golden-set.json")
    ap.add_argument("--library-id", type=int, default=None)
    ap.add_argument("--per-family", type=int, default=25,
                    help="cases per generated family (default 25)")
    args = ap.parse_args()

    db.init()
    libraries = db.list_libraries()
    if not libraries:
        raise SystemExit("No libraries in this database.")
    library_id = args.library_id or libraries[0].id

    loaded = LIBRARIES.get(library_id)
    if not loaded.is_loaded():
        raise SystemExit(f"Library {library_id} has no tracks.")

    prefs = db.preference_map(library_id)
    membership = db.playlist_membership(library_id)
    index = LibraryIndex(loaded.tracks)

    cases = (build_cases(loaded.tracks, args.per_family)
             + preference_cases(library_id)
             + playlist_cases(library_id, 25))

    records = [capture(c, index, prefs, membership) for c in cases]

    buckets: dict[str, int] = {}
    families: dict[str, dict[str, int]] = {}
    for r in records:
        bucket = r["expected"]["bucket"]
        buckets[bucket] = buckets.get(bucket, 0) + 1
        families.setdefault(r["family"], {})
        families[r["family"]][bucket] = families[r["family"]].get(bucket, 0) + 1

    payload = {
        "note": "Recorded behaviour of the Python matcher. Regenerate with "
                "scripts/golden_set.py; the Java port must reproduce it.",
        "seed": SEED,
        "source": {
            "database": os.environ["REKORD_DB"],
            "library_id": library_id,
            "library_name": loaded.name,
            "library_size": len(index.items),
            "preferences": len(prefs),
            "playlist_members": len(membership),
        },
        "thresholds": _thresholds(),
        "summary": {"cases": len(records), "by_bucket": buckets, "by_family": families},
        "cases": records,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"{len(records)} cases -> {args.out}")
    print(f"library {library_id} ({loaded.name}): {len(index.items)} tracks, "
          f"{len(prefs)} preferences")
    print("buckets:", ", ".join(f"{k}={v}" for k, v in sorted(buckets.items())))
    print()
    print(f"{'family':<16} {'auto':>6} {'ambig':>6} {'unmat':>6}")
    for fam, counts in sorted(families.items()):
        print(f"{fam:<16} {counts.get('auto', 0):>6} "
              f"{counts.get('ambiguous', 0):>6} {counts.get('unmatched', 0):>6}")


if __name__ == "__main__":
    main()
