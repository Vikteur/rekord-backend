import os
import time
from collections import Counter
from pathlib import Path

import pytest

from server import db
from server.library import LIBRARIES, LibraryCache, summary_for
from server.scanner.scan import Scanner
from tests.helpers import make_audio_tree

OWNER = 1  # any user id — the scanner itself doesn't care who owns a library


@pytest.fixture()
def lib_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "library.db")
    db.init()
    LIBRARIES.invalidate()
    return db.create_library("MacBook", owner_id=OWNER)


@pytest.fixture()
def library(tmp_path: Path, lib_id: int) -> Path:
    root = tmp_path / "music"
    make_audio_tree(root)
    return root


def scan(root: Path, library_id: int, force: bool = False) -> Scanner:
    scanner = Scanner()
    scanner.start_scan(library_id, str(root), force=force)
    scanner.wait()
    return scanner


def test_first_scan_finds_everything(library: Path, lib_id: int) -> None:
    scanner = scan(library, lib_id)
    status = scanner.status()
    assert status["state"] == "done"
    # 6 audio files (hidden dir skipped, notes.txt ignored), 1 DRM m4p counted.
    assert status["scanned"]["track_count"] == 6
    assert status["scanned"]["skipped_drm"] == 1
    assert status["library_id"] == lib_id
    assert status["parsed"] == 6
    assert status["from_cache"] == 0
    loaded = LIBRARIES.get(lib_id)
    assert Counter(track.ext for track in loaded.tracks) == {"mp3": 5, "wav": 1}
    # The corrupt file is reported but still present as a track.
    assert any("corrupt" in error["message"] for error in status["errors"])
    assert any(track.title == "corrupt" for track in loaded.tracks)
    assert len(loaded.by_id) == 6


def test_skipped_files_are_named_not_just_counted(library: Path, lib_id: int) -> None:
    """"75 DRM files skipped" is useless without knowing which ones."""
    status = scan(library, lib_id).status()

    drm = status["scanned"]["skipped_drm_files"]
    assert status["scanned"]["skipped_drm"] == len(drm) == 1
    assert drm[0].endswith("old-purchase.m4p")

    # Unreadable files say which file and why.
    unreadable = [error for error in status["errors"] if "corrupt" in error["file"]]
    assert len(unreadable) == 1
    assert unreadable[0]["message"], "an unreadable file must explain itself"


def test_second_scan_is_all_cache(library: Path, lib_id: int) -> None:
    scan(library, lib_id)
    scanner = scan(library, lib_id)
    status = scanner.status()
    assert status["parsed"] == 0
    assert status["from_cache"] == 6
    assert status["scanned"]["track_count"] == 6


def test_touched_file_is_reparsed_alone(library: Path, lib_id: int) -> None:
    scan(library, lib_id)
    target = library / "House" / "am-i-wrong.mp3"
    future = time.time() + 10
    os.utime(target, (future, future))
    scanner = scan(library, lib_id)
    status = scanner.status()
    assert status["parsed"] == 1
    assert status["from_cache"] == 5


def test_force_ignores_cache(library: Path, lib_id: int) -> None:
    scan(library, lib_id)
    scanner = scan(library, lib_id, force=True)
    assert scanner.status()["parsed"] == 6


def test_deleted_file_leaves_library(library: Path, lib_id: int) -> None:
    scan(library, lib_id)
    (library / "Untagged" / "random_name.mp3").unlink()
    scan(library, lib_id)
    # The scan invalidated the cache entry, so this read sees the removal.
    tracks = LIBRARIES.get(lib_id).tracks
    assert len(tracks) == 5
    assert all("random_name" not in track.path for track in tracks)


def test_library_survives_a_restart(library: Path, lib_id: int) -> None:
    """The whole point of the database: a fresh process needs no rescan."""
    scan(library, lib_id)

    restarted = LibraryCache()  # a fresh process = an empty cache
    loaded = restarted.get(lib_id)
    assert len(loaded.tracks) == 6
    assert loaded.is_loaded() is True
    assert loaded.name == "MacBook"
    assert summary_for(OWNER, False)["sources"][0]["kind"] == "folder"


def test_scanning_into_a_second_library_keeps_them_separate(
    library: Path, lib_id: int
) -> None:
    scan(library, lib_id)
    other = db.create_library("Studio PC", owner_id=OWNER)
    scan(library, other)

    counts = {info.name: info.track_count for info in db.list_libraries()}
    assert counts == {"MacBook": 6, "Studio PC": 6}
    # Both libraries reference the same files, stored once.
    assert len(db.all_tracks()) == 6
    # The owner's selection is unchanged by scanning into another library.
    assert db.active_library_id(OWNER) == lib_id


def test_rescanning_a_folder_does_not_duplicate_tracks(
    library: Path, lib_id: int
) -> None:
    scan(library, lib_id)
    scan(library, lib_id)
    scan(library, lib_id, force=True)
    assert len(LIBRARIES.get(lib_id).tracks) == 6
    assert len(db.list_sources(lib_id)) == 1


def test_missing_folder_errors_cleanly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "library.db")
    db.init()
    scanner = Scanner()
    scanner.start_scan(db.create_library("Empty"), str(tmp_path / "nope"))
    scanner.wait()
    status = scanner.status()
    assert status["state"] == "done"
    assert status["scanned"]["track_count"] == 0
