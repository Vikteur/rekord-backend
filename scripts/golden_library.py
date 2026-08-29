"""Export the library the golden set was recorded against.

The golden set alone is not enough to check a port: track ids are derived from
file paths, and candidate selection depends on how rare each token is across
the *whole* library, so a subset would not behave the same. The two files go
together.

Written compactly — arrays rather than objects, durations rounded to the
precision the matcher actually uses — because this is 20,000-odd rows that live
in a repository.

    REKORD_DB=/abs/snapshot.db python -m scripts.golden_library --out golden-library.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

if not os.environ.get("REKORD_DB"):
    sys.exit("Set REKORD_DB to a snapshot.")

from server import db  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="golden-library.json")
    ap.add_argument("--library-id", type=int, default=None)
    args = ap.parse_args()

    db.init()
    libraries = db.list_libraries()
    if not libraries:
        raise SystemExit("No libraries in this database.")
    library_id = args.library_id or libraries[0].id

    tracks = [
        {
            "id": t.id,
            "artist": t.artist,
            "title": t.title,
            "duration_sec": round(t.duration_sec, 3) if t.duration_sec is not None else None,
        }
        for t in db.library_tracks(library_id)
    ]

    payload = {
        "note": "The library the golden set was recorded against. Regenerate the "
                "two together; neither is meaningful alone.",
        "library_id": library_id,
        "tracks": tracks,
        # Remembered choices, and rekordbox playlist membership — both change
        # what the matcher returns, so both belong in the fixture.
        "preferences": db.preference_map(library_id),
        "membership": db.playlist_membership(library_id),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write("\n")

    size = os.path.getsize(args.out)
    print(f"{len(tracks)} tracks, {len(payload['preferences'])} preferences -> "
          f"{args.out} ({size / 1_048_576:.1f} MiB)")


if __name__ == "__main__":
    main()
