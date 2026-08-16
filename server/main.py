import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import auth, couples, db
from server.auth_api import require_user, router as auth_router
from server.couples_api import router as couples_router
from server.export.m3u8 import build_m3u8
from server.export.missing import build_missing_txt
from server.export.skipped import build_skipped_txt
from server.export.rekordbox_xml import build_rekordbox_xml
from server.library import LIBRARIES, LoadedLibrary, summary_for
from server.matcher.index import LibraryIndex
from server.matcher.match import match_playlist
from server.matcher.signature import signature_id, signature_of
from server.models import MissingTrackInput, PlaylistTrackInput
from server.playlist_import import (
    PlaylistImportError,
    parse_playlist,
    resolve_entries,
)
from server.rekordbox_import import RekordboxXmlError, parse_collection
from server.scanner.scan import SCANNER, ScanInProgress
from server.spotify.fetch import SpotifyFetchError, fetch_playlist
from server.spotify.parse_embed import (
    BadPlaylistUrl,
    EmbedParseError,
    parse_playlist_url,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Libraries load lazily per user; a restart still needs no rescan.
    db.init()
    auth.init()
    couples.init()
    auth.ensure_admin_from_env()
    yield


app = FastAPI(title="spotify-to-rekordbox", lifespan=lifespan)

# Module-level so tests can swap in a fixture-backed fake.
playlist_fetcher = fetch_playlist

_PASTE_HINT = "Use the paste-text fallback: one 'Artist - Title' per line."
MAX_XML_BYTES = 256 * 1024 * 1024


class ScanRequest(BaseModel):
    folder: str
    force: bool = False
    library_id: int | None = None   # defaults to the active library


class LibraryRequest(BaseModel):
    name: str


class PlaylistRequest(BaseModel):
    url: str


class MatchRequest(BaseModel):
    tracks: list[PlaylistTrackInput]
    playlist_id: int | None = None   # narrow matching to one imported playlist


class ExportRequest(BaseModel):
    name: str
    format: str  # "m3u8" | "xml"
    track_ids: list[str]
    couple_id: int | None = None   # apply this couple's never list


class MissingExportRequest(BaseModel):
    name: str
    tracks: list[MissingTrackInput]
    couple_id: int | None = None


class PreferenceRequest(BaseModel):
    artist: str = ""
    title: str
    track_id: str


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _count_missing_files(tracks: list) -> int:
    """How many imported paths aren't on this machine (drive not connected?).

    Checks each directory once first: when a whole drive is absent — the common
    case — that answers for every file under it without a stat per track.
    """
    directory_exists: dict[str, bool] = {}
    missing = 0
    for track in tracks:
        parent = os.path.dirname(track.path)
        present = directory_exists.get(parent)
        if present is None:
            present = os.path.isdir(parent)
            directory_exists[parent] = present
        if not present or not os.path.exists(track.path):
            missing += 1
    return missing


# (library_id, playlist_id) -> (generation, index). A LoadedLibrary snapshot
# is immutable once handed out, so a stale generation simply rebuilds; worst
# case under concurrent matches is a redundant rebuild, never a torn read.
_index_cache: dict[tuple[int, int | None], tuple[int, LibraryIndex]] = {}
_INDEX_CACHE_MAX = 4


def _get_index(library: LoadedLibrary, playlist_id: int | None = None) -> LibraryIndex:
    """The matching index for one library, optionally narrowed to a playlist."""
    key = (library.id, playlist_id)
    hit = _index_cache.get(key)
    if hit is not None and hit[0] == library.generation:
        return hit[1]
    tracks = library.tracks
    if playlist_id is not None:
        allowed = db.playlist_track_ids(playlist_id)
        tracks = [track for track in tracks if track.id in allowed]
    index = LibraryIndex(tracks)
    _index_cache[key] = (library.generation, index)
    while len(_index_cache) > _INDEX_CACHE_MAX:  # drop the oldest entry
        _index_cache.pop(next(iter(_index_cache)))
    return index


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


# --- libraries -------------------------------------------------------------

def _require_library(user: auth.CurrentUser, library_id: int | None) -> int:
    """The library a request targets: the one asked for, else the user's
    active one. Someone else's library answers 404, exactly like a missing
    one, so ids can't be probed."""
    if library_id is None:
        library_id = db.active_library_id(user.id, user.is_admin)
    if library_id is None:
        raise _error(
            409, "NO_LIBRARY_SELECTED", "Create a library first, then add music to it."
        )
    if not db.library_visible(library_id, user.id, user.is_admin):
        raise _error(404, "NO_LIBRARY", f"No library with id {library_id}.")
    return library_id


def _active_library(user: auth.CurrentUser) -> LoadedLibrary | None:
    library_id = db.active_library_id(user.id, user.is_admin)
    return LIBRARIES.get(library_id) if library_id is not None else None


@app.get("/api/library")
def library(user: auth.CurrentUser = Depends(require_user)) -> dict:
    return summary_for(user.id, user.is_admin)


@app.post("/api/libraries", status_code=201)
def create_library(
    request: LibraryRequest, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    name = request.name.strip()
    if not name:
        raise _error(400, "EMPTY_NAME", "Give the library a name.")
    try:
        library_id = db.create_library(name, owner_id=user.id)
    except db.DuplicateLibraryName as exc:
        raise _error(409, "DUPLICATE_NAME", str(exc))
    db.set_active_library_id(user.id, library_id)  # a new library becomes active
    return summary_for(user.id, user.is_admin)


@app.post("/api/libraries/{library_id}/select")
def select_library(
    library_id: int, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    if not db.library_visible(library_id, user.id, user.is_admin):
        raise _error(404, "NO_LIBRARY", f"No library with id {library_id}.")
    db.set_active_library_id(user.id, library_id)
    return summary_for(user.id, user.is_admin)


@app.patch("/api/libraries/{library_id}")
def rename_library(
    library_id: int, request: LibraryRequest,
    user: auth.CurrentUser = Depends(require_user),
) -> dict:
    name = request.name.strip()
    if not name:
        raise _error(400, "EMPTY_NAME", "Give the library a name.")
    if not db.library_visible(library_id, user.id, user.is_admin):
        raise _error(404, "NO_LIBRARY", f"No library with id {library_id}.")
    try:
        db.rename_library(library_id, name)
    except db.DuplicateLibraryName as exc:
        raise _error(409, "DUPLICATE_NAME", str(exc))
    LIBRARIES.invalidate(library_id)  # the cached entry carries the old name
    return summary_for(user.id, user.is_admin)


@app.delete("/api/libraries/{library_id}")
def delete_library(
    library_id: int, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    if not db.library_visible(library_id, user.id, user.is_admin):
        raise _error(404, "NO_LIBRARY", f"No library with id {library_id}.")
    db.delete_library(library_id)
    LIBRARIES.invalidate(library_id)
    return summary_for(user.id, user.is_admin)


# --- library sources -------------------------------------------------------

@app.delete("/api/library/sources/{source_id}")
def remove_source(
    source_id: int, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    library_id = db.source_library_id(source_id)
    if library_id is None or not db.library_visible(
        library_id, user.id, user.is_admin
    ):
        raise _error(404, "NO_SOURCE", f"No library source with id {source_id}.")
    db.delete_source(source_id)
    LIBRARIES.invalidate(library_id)
    return summary_for(user.id, user.is_admin)


@app.post("/api/library/xml")
async def import_rekordbox_xml(
    request: Request, name: str = "rekordbox.xml", library_id: int | None = None,
    user: auth.CurrentUser = Depends(require_user),
) -> dict:
    """Import a rekordbox collection XML export (raw request body, not multipart)."""
    target = _require_library(user, library_id)
    data = await request.body()
    if not data:
        raise _error(400, "EMPTY_FILE", "No XML content was uploaded.")
    if len(data) > MAX_XML_BYTES:
        raise _error(413, "FILE_TOO_LARGE", "That XML export is unexpectedly large.")
    try:
        tracks, warnings = parse_collection(data)
    except RekordboxXmlError as exc:
        raise _error(400, "BAD_XML", str(exc))

    source_id = db.upsert_source(target, "xml", name)
    db.replace_source_tracks(source_id, tracks)
    LIBRARIES.invalidate(target)

    missing = _count_missing_files(tracks)
    return {
        "imported": len(tracks),
        "missing_files": missing,
        "warnings": warnings[:20],
        "library": summary_for(user.id, user.is_admin),
    }


# --- imported rekordbox playlists ------------------------------------------

@app.post("/api/library/playlists")
async def import_playlist(
    request: Request, name: str = "", library_id: int | None = None,
    user: auth.CurrentUser = Depends(require_user),
) -> dict:
    """Import a playlist exported from rekordbox (raw body, not multipart)."""
    target = _require_library(user, library_id)
    loaded = LIBRARIES.get(target)
    if not loaded.is_loaded():
        raise _error(
            409,
            "NO_LIBRARY",
            "Scan or import your music first — a playlist is matched against it.",
        )
    data = await request.body()
    if len(data) > MAX_XML_BYTES:
        raise _error(413, "FILE_TOO_LARGE", "That playlist file is unexpectedly large.")
    try:
        default_name, entries = parse_playlist(data, name)
    except PlaylistImportError as exc:
        raise _error(400, "BAD_PLAYLIST", str(exc))

    resolved, missing = resolve_entries(entries, _get_index(loaded), loaded.by_id)
    if not resolved:
        raise _error(
            400,
            "NOTHING_RESOLVED",
            f"None of the {len(entries)} tracks in that playlist are in "
            f"“{loaded.name}”. Is it a playlist from a different device?",
        )
    playlist_id = db.replace_playlist(target, default_name, resolved, len(missing))
    return {
        "playlist_id": playlist_id,
        "name": default_name,
        "resolved": len(resolved),
        "missing": len(missing),
        "missing_examples": [
            f"{entry.artist} - {entry.title}".strip(" -") or (entry.path or "?")
            for entry in missing[:5]
        ],
        "playlists": [p.model_dump() for p in db.list_playlists(target)],
    }


@app.get("/api/library/playlists")
def get_playlists(user: auth.CurrentUser = Depends(require_user)) -> dict:
    library_id = db.active_library_id(user.id, user.is_admin)
    if library_id is None:
        return {"playlists": []}
    return {"playlists": [p.model_dump() for p in db.list_playlists(library_id)]}


@app.get("/api/library/playlists/{playlist_id}/tracks")
def get_playlist_tracks(
    playlist_id: int, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    """What's actually in an imported playlist, in its exported order."""
    library_id = _require_library(user, None)
    if playlist_id not in {p.id for p in db.list_playlists(library_id)}:
        raise _error(404, "NO_PLAYLIST", f"No playlist with id {playlist_id}.")
    return {"tracks": [track.model_dump() for track in db.playlist_tracks(playlist_id)]}


@app.delete("/api/library/playlists/{playlist_id}")
def remove_playlist(
    playlist_id: int, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    library_id = _require_library(user, None)
    if not db.delete_playlist(library_id, playlist_id):
        raise _error(404, "NO_PLAYLIST", f"No playlist with id {playlist_id}.")
    return {"playlists": [p.model_dump() for p in db.list_playlists(library_id)]}


# --- folder scanning -------------------------------------------------------

@app.post("/api/scan", status_code=202)
def start_scan(
    request: ScanRequest, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    target = _require_library(user, request.library_id)
    folder = request.folder.strip().strip("\"'")
    if not folder:
        raise _error(400, "EMPTY_FOLDER", "Enter a folder path to scan.")
    path = Path(folder).expanduser()
    if not path.is_dir():
        raise _error(
            404, "FOLDER_NOT_FOUND", f"Not a folder (or not readable): {path}"
        )
    try:
        SCANNER.start_scan(target, str(path), force=request.force)
    except ScanInProgress:
        raise _error(409, "SCAN_IN_PROGRESS", "A scan is already running.")
    return {"started": True, "library_id": target}


@app.get("/api/scan/status")
def scan_status(user: auth.CurrentUser = Depends(require_user)) -> dict:
    del user
    return SCANNER.status()


# --- playlist, matching, export --------------------------------------------

@app.post("/api/spotify/playlist")
def spotify_playlist(
    request: PlaylistRequest, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    del user
    try:
        playlist_id = parse_playlist_url(request.url)
    except BadPlaylistUrl as exc:
        raise _error(400, "BAD_URL", str(exc))
    try:
        return playlist_fetcher(playlist_id)
    except SpotifyFetchError as exc:
        raise _error(502, "SPOTIFY_FETCH_FAILED", f"{exc} {_PASTE_HINT}")
    except EmbedParseError as exc:
        raise _error(502, "SPOTIFY_PARSE_FAILED", f"{exc} {_PASTE_HINT}")


@app.post("/api/match")
def match(
    request: MatchRequest, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    if SCANNER.is_scanning():
        raise _error(409, "SCAN_IN_PROGRESS", "Wait for the scan to finish.")
    loaded = _active_library(user)
    if loaded is None or not loaded.is_loaded():
        raise _error(
            409,
            "NO_LIBRARY",
            "The selected library is empty: scan a folder or import a rekordbox XML.",
        )
    if not request.tracks:
        raise _error(400, "NO_TRACKS", "The playlist has no tracks.")
    index = _get_index(loaded, request.playlist_id)
    results = match_playlist(
        request.tracks,
        index,
        db.preference_map(loaded.id),
        db.playlist_membership(loaded.id),
    )
    return {
        "results": [result.model_dump() for result in results],
        "library_size": len(index.items),
        "library_name": loaded.name,
    }


# --- remembered version choices --------------------------------------------

def _preferences_payload(user: auth.CurrentUser) -> dict:
    library_id = db.active_library_id(user.id, user.is_admin)
    if library_id is None:
        return {"preferences": []}
    return {"preferences": [p.model_dump() for p in db.list_preferences(library_id)]}


@app.get("/api/preferences")
def get_preferences(user: auth.CurrentUser = Depends(require_user)) -> dict:
    return _preferences_payload(user)


@app.post("/api/preferences")
def save_preference(
    request: PreferenceRequest, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    """Remember this file as the default for this song in the active library."""
    library_id = _require_library(user, None)
    if request.track_id not in LIBRARIES.get(library_id).by_id:
        raise _error(400, "UNKNOWN_TRACK", f"Unknown track id {request.track_id!r}.")
    db.save_preference(
        library_id,
        signature_id(request.artist, request.title),
        signature_of(request.artist, request.title),
        request.artist,
        request.title,
        request.track_id,
    )
    return _preferences_payload(user)


@app.delete("/api/preferences/{preference_id}")
def forget_preference(
    preference_id: str, user: auth.CurrentUser = Depends(require_user)
) -> dict:
    library_id = _require_library(user, None)
    if not db.delete_preference(library_id, preference_id):
        raise _error(404, "NO_PREFERENCE", "No remembered choice with that id.")
    return _preferences_payload(user)


@app.delete("/api/preferences")
def forget_all_preferences(user: auth.CurrentUser = Depends(require_user)) -> dict:
    db.clear_preferences(_require_library(user, None))
    return {"preferences": []}


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w \-]", "", name, flags=re.ASCII).strip()
    return cleaned or "playlist"


def _require_couple_visible(user: auth.CurrentUser, couple_id: int | None) -> None:
    """An export may only reference a couple its caller could open."""
    if couple_id is None:
        return
    couple = couples.get_couple(couple_id)
    if couple is None or not (user.is_admin or couple["dj_id"] == user.id):
        raise _error(404, "NO_COUPLE", f"No couple with id {couple_id}.")


def _drop_blocked(tracks: list, couple_id: int | None) -> list:
    """A couple's never list keeps its songs out of *every* export for them."""
    if couple_id is None:
        return tracks
    keys = couples.blocked_keys(couple_id)
    return [
        track for track in tracks
        if not couples.is_blocked(track.artist, track.title, keys)
    ]


@app.post("/api/export")
def export(
    request: ExportRequest, user: auth.CurrentUser = Depends(require_user)
) -> Response:
    _require_couple_visible(user, request.couple_id)
    loaded = _active_library(user)
    if loaded is None or not loaded.is_loaded():
        raise _error(409, "NO_LIBRARY", "Add a library first.")
    tracks = []
    for track_id in request.track_ids:
        track = loaded.by_id.get(track_id)
        if track is None:
            raise _error(400, "UNKNOWN_TRACK", f"Unknown track id {track_id!r}.")
        tracks.append(track)
    tracks = _drop_blocked(tracks, request.couple_id)
    if not tracks:
        raise _error(
            400, "NO_TRACKS",
            "Nothing selected to export."
            if request.couple_id is None
            else "Nothing left to export — everything selected is on the couple's never list.",
        )

    stem = _safe_filename(request.name)
    if request.format == "m3u8":
        content = build_m3u8(tracks)
        media_type = "audio/x-mpegurl; charset=utf-8"
        filename = f"{stem}.m3u8"
    elif request.format == "xml":
        content = build_rekordbox_xml(request.name, tracks)
        media_type = "application/xml; charset=utf-8"
        filename = f"{stem}.rekordbox.xml"
    else:
        raise _error(400, "BAD_FORMAT", "format must be 'm3u8' or 'xml'.")
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/export/skipped")
def export_skipped(user: auth.CurrentUser = Depends(require_user)) -> Response:
    """What the last scan could not use: DRM-locked and unreadable files."""
    del user
    status = SCANNER.status()
    scanned = status.get("scanned") or {}
    errors = status.get("errors") or []
    drm_files = scanned.get("skipped_drm_files") or []
    drm_total = scanned.get("skipped_drm", 0)
    if not drm_files and not errors:
        raise _error(
            400, "NOTHING_SKIPPED", "The last scan skipped nothing — there's no list."
        )
    content = build_skipped_txt(
        scanned.get("folder", "(unknown folder)"), drm_files, drm_total, errors
    )
    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="skipped files.txt"'},
    )


@app.post("/api/export/missing")
def export_missing(
    request: MissingExportRequest, user: auth.CurrentUser = Depends(require_user)
) -> Response:
    """The playlist's tracks that this library doesn't have — a shopping list."""
    _require_couple_visible(user, request.couple_id)
    tracks = request.tracks
    if request.couple_id is not None:
        keys = couples.blocked_keys(request.couple_id)
        tracks = [t for t in tracks if not couples.is_blocked(t.artist, t.title, keys)]
    if not tracks:
        raise _error(400, "NO_TRACKS", "Nothing is missing — there's nothing to list.")
    loaded = _active_library(user)
    content = build_missing_txt(
        request.name, loaded.name if loaded else None, tracks
    )
    stem = _safe_filename(request.name)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{stem} - missing.txt"'
        },
    )


# Sign-in, sessions and DJ-account management.
app.include_router(auth_router)

# Couple intake + guest magic-link routes.
app.include_router(couples_router)

# When the client has been built (npm run build), serve it so the whole app
# runs from uvicorn alone. Mounted last so /api routes take precedence.
DIST = Path(__file__).resolve().parent.parent / "dist"


@app.get("/g/{token}")
def guest_page(token: str) -> Response:
    """Serve the SPA for magic links; the client reads the token from the URL."""
    del token
    index = DIST / "index.html"
    if not index.is_file():
        raise _error(503, "NO_BUILD", "Run `npm run build` first (or open the vite dev URL).")
    return FileResponse(index)


if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="static")
