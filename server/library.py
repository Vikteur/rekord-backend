"""Loaded libraries, cached in memory: what playlists are matched against.

With per-DJ libraries there is no single "active" library any more — each
signed-in user has their own selection (a `settings` row per user). This
cache holds the last few loaded libraries so switching users or libraries
doesn't re-read thousands of track rows per request; a write to a library
(`invalidate`) drops its entry, and the bumped `generation` on the next load
tells the matcher to rebuild its inverted index.
"""

import threading

from server import db
from server.models import LibraryTrack

# Libraries kept in memory at once. Small on purpose: a couple of DJs each
# working their own library, not a fleet.
CACHE_MAX = 4


class LoadedLibrary:
    """One library's tracks, as read from SQLite at `generation` time."""

    def __init__(self, library_id: int, name: str | None,
                 tracks: list[LibraryTrack], generation: int) -> None:
        self.id = library_id
        self.name = name
        self.tracks = tracks
        self.by_id: dict[str, LibraryTrack] = {track.id: track for track in tracks}
        self.generation = generation

    def is_loaded(self) -> bool:
        return bool(self.tracks)


class LibraryCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[int, LoadedLibrary] = {}
        self._generation = 0

    def get(self, library_id: int) -> LoadedLibrary:
        """The cached library, read from SQLite on a miss."""
        with self._lock:
            entry = self._entries.get(library_id)
            if entry is not None:
                return entry
            self._generation += 1
            generation = self._generation
        # Read outside the lock: a big library takes a moment.
        tracks = db.library_tracks(library_id)
        name = next(
            (lib.name for lib in db.list_libraries() if lib.id == library_id), None
        )
        entry = LoadedLibrary(library_id, name, tracks, generation)
        with self._lock:
            self._entries[library_id] = entry
            while len(self._entries) > CACHE_MAX:  # drop the oldest entry
                self._entries.pop(next(iter(self._entries)))
        return entry

    def invalidate(self, library_id: int | None = None) -> None:
        """Forget one library (or all) after a write; the next get() reloads."""
        with self._lock:
            if library_id is None:
                self._entries.clear()
            else:
                self._entries.pop(library_id, None)


LIBRARIES = LibraryCache()


def summary_for(user_id: int, is_admin: bool) -> dict:
    """The library panel payload, seen through one user's eyes: their own
    libraries (all of them for the admin) and their own active selection."""
    active_id = db.active_library_id(user_id, is_admin)
    active = LIBRARIES.get(active_id) if active_id is not None else None
    by_ext: dict[str, int] = {}
    if active is not None:
        for track in active.tracks:
            by_ext[track.ext] = by_ext.get(track.ext, 0) + 1
    return {
        "active_library_id": active_id,
        "active_library_name": active.name if active else None,
        "track_count": len(active.tracks) if active else 0,
        "by_ext": by_ext,
        "libraries": [
            lib.model_dump()
            for lib in db.list_libraries(None if is_admin else user_id)
        ],
        "sources": (
            [source.model_dump() for source in db.list_sources(active_id)]
            if active_id is not None
            else []
        ),
    }
