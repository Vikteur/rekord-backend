# The matcher golden set

`golden-set.json` records what `server/matcher/` **does**, so the Java port can
prove it does the same thing.

## Why this exists

The thresholds in `server/matcher/score.py` are calibrated against rapidfuzz's
exact numbers. `token_sort_ratio` and `token_set_ratio` are specific
Indel-distance algorithms with specific tokenisation and rounding, and no Java
library reproduces them — `me.xdrop:fuzzywuzzy` is the closest port of the same
semantics and still returns different values. Every constant in `score.py`
(`AUTO_SCORE 0.82`, `AUTO_MARGIN 0.10`, `AUTO_MIN_VERSION 0.90`, the five
weights) is tuned to the numbers rapidfuzz happens to give.

`docs/business-analysis.md` §11.1 is candid that matching accuracy has never
been measured — "auto is confident" is a design assertion, not a metric. So
before this file existed, nothing in the project would have noticed a port
quietly getting the matching wrong.

## What it is and is not

It records **behaviour, not correctness**. A wrong-but-recorded answer still
belongs here. The question a port has to answer is *"did I change the
behaviour"*, which is a different question from *"is the behaviour good"*.
Measuring quality needs hand-labelled ground truth and is a separate exercise —
the one §11.1 proposes.

So: a failing case means the port diverged. It does not by itself mean the port
is worse.

## The snapshot is half the artifact

Track ids are `sha1(path)[:12]`, so every expectation in this file is tied to
one specific library. **`golden-set.json` is meaningless without the database
snapshot it was generated from.** The snapshot is ~10 MB and is not committed;
regenerate the pair together, and keep them together.

Current contents were generated from library 1 ("dekstop"): 20,869 tracks,
4 sources, 9 remembered preferences, 1 imported rekordbox playlist.

## Regenerating

Take the snapshot with SQLite's backup API, never `cp` — a plain copy of a
database in WAL mode can tear, and the tables may live entirely in the `-wal`
file:

```python
import sqlite3
src = sqlite3.connect("file:data/library.db?mode=ro", uri=True)
dst = sqlite3.connect("/abs/path/snapshot.db")
src.backup(dst); dst.close(); src.close()
```

Then:

```bash
REKORD_DB=/abs/path/snapshot.db python -m scripts.golden_set \
    --out tests/golden/golden-set.json
```

Use an **absolute** path. On Windows, Git Bash's `/tmp` and Python's
`Path("/tmp")` resolve to different directories, and the script will silently
create and migrate an empty database instead of reading yours.

Generation is deterministic — fixed `SEED`, sorted sampling pool — so the same
snapshot always produces a byte-identical file. A diff means something changed.

Opening the snapshot runs schema migrations, which write to it. That is why the
script refuses to run without `REKORD_DB` set: it must never touch
`data/library.db`.

## Reading a case

```jsonc
{
  "family": "core_only",              // what is being probed
  "note": "file has a version suffix, query does not",
  "derived_from": "6fe637969c06",     // diagnosis only — NOT an assertion
  "query":    { "artist": "...", "title": "...", "duration_sec": 195.0 },
  "expected": {
    "bucket": "ambiguous",            // auto | ambiguous | unmatched
    "auto_selected_id": null,
    "from_preference": false,
    "candidates": [ { "score": 0.8657, "parts": { ... } } ]   // 6 dp
  }
}
```

`derived_from` is the library track a query was built from. It is recorded to
make failures diagnosable, **not** as the expected answer — several families
deliberately make that track unlikely to win.

Scores are rounded to 6 places: far tighter than the closest threshold gap
(`AUTO_MARGIN`, 0.10), so real differences show up without float noise looking
like one. `thresholds` pins every constant from `score.py`, so editing one
surfaces as a diff here rather than as a silent behaviour change.

## The families

| Family | Probes |
| --- | --- |
| `exact` | artist and title straight off the file — the floor |
| `core_only` | file has `(Extended Mix)`, query does not — the most common real mismatch |
| `added_version` | query asks for a version the file does not name; `version_score` must block the auto-pick |
| `typo` | one mistyped character — the fuzzy scorer rather than the token index |
| `no_artist` | title only; drops the artist facet |
| `ampersand` | `&` vs `and` — proves the port's `normalize()` folds them |
| `feat_inline` | featured artist folded into the title, as Spotify writes it |
| `case_punct` | uppercased, punctuation stripped |
| `duration_off` | correct song, duration 45 s out — isolates `duration_score` |
| `unowned` | not in the library; nothing may be auto-picked |
| `preference` | the 9 real remembered choices |
| `playlist_member` | in an imported rekordbox playlist, so `PLAYLIST_BONUS` applies |

## Two behaviours that are easy to port wrong

Both are pinned by cases in this file.

**A preference sets the auto-pick but does not change the bucket.** In
`match.py`, `_bucket()` runs first, then the preference override rewrites
`auto_selected_id` and sets `from_preference`, leaving `bucket` alone. All 9
`preference` cases therefore record `bucket: "ambiguous"` *with* a non-null
`auto_selected_id`. A port that recomputes the bucket after applying the
preference will pass a naive smoke test and fail here.

**The playlist bonus orders candidates but never promotes them.**
`PLAYLIST_BONUS` is applied in `_ranked()` for sorting only; `_bucket()` reads
the raw score. A most-played file can top the list without crossing the auto
threshold.

## Why so many `exact` cases are `ambiguous`

47 of 212 cases land in `auto`, and only 6 of 25 `exact` ones. That is correct
for this library, not a fault in the harness.

The library contains genuine duplicate files — 25,010 `track_sources` rows for
20,869 tracks, and `tracks.id` is derived from the file path, so the same song
at two paths is two rows. When two identical candidates both score `1.0000`,
`AUTO_MARGIN` (best − second ≥ 0.10) is not met and the matcher correctly
declines to guess which file you meant.

Expect a cleaner library to shift this distribution. That is a property of the
input, so a port must be compared against **this** snapshot, not a different
one.
