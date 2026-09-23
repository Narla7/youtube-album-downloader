#!/usr/bin/env python3
"""ytalbum - download albums from YouTube by name via yt-dlp."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

VERSION = "0.1.0"
ILLEGAL_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
VIDEO_DUR_MIN = 1500  # seconds; a "full album" video should be at least this long


@dataclass
class Candidate:
    ie_key: str
    id: str
    duration: int | None
    title: str
    score: int = 0

    @property
    def is_playlist(self) -> bool:
        return self.id.startswith(("PL", "OLAK"))

    @property
    def url(self) -> str:
        if self.is_playlist:
            return f"https://www.youtube.com/playlist?list={self.id}"
        return f"https://www.youtube.com/watch?v={self.id}"


def die(msg: str, code: int = 1) -> None:
    print(f"ytalbum: error: {msg}", file=sys.stderr)
    sys.exit(code)


def find_ytdlp() -> str:
    path = shutil.which("yt-dlp")
    if not path:
        die("yt-dlp not found on PATH. Install it: https://github.com/yt-dlp/yt-dlp#installation")
    return path


def find_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        print(
            "ytalbum: warning: ffmpeg not found - audio conversion, tagging and "
            "thumbnail embedding will fail. Install ffmpeg.",
            file=sys.stderr,
        )


def parse_album_query(query: str, artist: str | None) -> tuple[str, str | None]:
    """Split 'In Rainbows by Radiohead' into (album, artist)."""
    album = query.strip().replace("_", " ")
    found_artist = artist
    if not found_artist:
        m = re.split(r"\s+by\s+", album, maxsplit=1, flags=re.IGNORECASE)
        if len(m) == 2:
            album, found_artist = m[0].strip(), m[1].strip()
    album = ILLEGAL_FS_CHARS.sub("", album).strip()
    if found_artist:
        found_artist = ILLEGAL_FS_CHARS.sub("", found_artist).strip()
    if not album:
        die("empty album name")
    return album, (found_artist or None)


def slug(name: str) -> str:
    return ILLEGAL_FS_CHARS.sub("", name).strip() or "Unknown"


def build_search_url(query: str, max_results: int) -> str:
    # Direct results URL (unlike the ytsearch: prefix) also returns playlists.
    q = urllib.parse.quote_plus(f"{query} full album")
    return f"https://www.youtube.com/results?search_query={q}"


def search_candidates(ytdlp: str, query: str, max_results: int, verbose: bool) -> list[Candidate]:
    url = build_search_url(query, max_results)
    cmd = [
        ytdlp,
        "--flat-playlist",
        "--playlist-end",
        str(max_results),
        "--print",
        "%(ie_key)s\t%(id)s\t%(duration)s\t%(title)s",
        url,
    ]
    if verbose:
        print(f"+ {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 and not proc.stdout.strip():
        tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
        die(f"yt-dlp search failed:\n{tail}")

    candidates: list[Candidate] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        ie_key, vid, duration_s, title = (p.strip() for p in parts)
        if vid.startswith(("UC", "RD", "TL", "UUK")) and not vid.startswith(("PL", "OLAK")):
            continue  # channels / radios / mixes
        try:
            duration: int | None = int(duration_s) if duration_s not in ("NA", "None", "") else None
        except ValueError:
            duration = None
        candidates.append(Candidate(ie_key, vid, duration, title))
    return candidates


def score_candidate(c: Candidate, album: str, artist: str | None) -> int:
    t = c.title.lower()
    a = album.lower()
    ar = (artist or "").lower()
    s = 0
    if not c.is_playlist:
        if c.duration and c.duration >= VIDEO_DUR_MIN:
            s += 10
        if "full album" in t:
            s += 20
        elif "album" in t:
            s += 8
        if c.duration and c.duration < 600:
            s -= 30
    else:
        if c.id.startswith("OLAK"):  # auto-generated YouTube Music album
            s += 60
        if "full album" in t:
            s += 15
    if a and a in t:
        s += 50
    if ar and ar in t:
        s += 30
    if re.search(r"\b(disc|disk|cd)\s*2\b", t):
        s -= 50
    if "lyrics" in t:
        s -= 40
    if "best of" in t or "greatest" in t or "hits" in t:
        s -= 50
    if "commentary" in t or "interview" in t or "reaction" in t:
        s -= 50
    if "from the basement" in t or "scotch mist" in t or "live at" in t:
        s -= 25
    return s


def rank(candidates: list[Candidate], album: str, artist: str | None) -> list[Candidate]:
    for c in candidates:
        c.score = score_candidate(c, album, artist)
    # Playlists first (best score wins within each group), then videos.
    playlists = sorted((c for c in candidates if c.is_playlist), key=lambda c: -c.score)
    videos = sorted((c for c in candidates if not c.is_playlist), key=lambda c: -c.score)
    return playlists + videos


def print_candidates(candidates: list[Candidate], album: str, artist: str | None) -> None:
    print(f"Search results for: {album}" + (f" by {artist}" if artist else ""))
    print(f"{'#':>3}  {'TYPE':<9} {'SCORE':>5}  {'ID':<24} TITLE")
    for i, c in enumerate(candidates, 1):
        kind = "playlist" if c.is_playlist else "video"
        dur = f" [{c.duration}s]" if c.duration and not c.is_playlist else ""
        print(f"{i:>3}  {kind:<9} {c.score:>5}  {c.id:<24} {c.title}{dur}")
    if not candidates:
        print("(no results)")


def build_download_cmd(
    ytdlp: str,
    target: str,
    outdir: Path,
    fmt: str,
    quality: str,
    items: str | None,
    cookies: str | None,
    cookies_from_browser: str | None,
    extractor_args: list[str],
    keep_video: bool,
    verbose: bool,
    extra: list[str],
) -> list[str]:
    is_playlist = "list=" in target
    cmd = [
        ytdlp,
        "--yes-playlist" if is_playlist else "--no-playlist",
        "--embed-metadata",
        "--embed-thumbnail",
        "--concurrent-fragments",
        "4",
        "--paths",
        str(outdir),
        "--output",
        "%(playlist_index)02d - %(title)s.%(ext)s"
        if is_playlist
        else "%(title)s.%(ext)s",
        "--audio-format",
        fmt,
        "--audio-quality",
        quality,
    ]
    if not keep_video:
        cmd.append("-x")
    if items:
        cmd += ["--playlist-items", items]
    if cookies:
        cmd += ["--cookies", cookies]
    if cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    for ea in extractor_args:
        cmd += ["--extractor-args", ea]
    if verbose:
        cmd.append("--verbose")
    cmd += extra
    cmd.append(target)
    return cmd


def pick_target(
    candidates: list[Candidate], album: str, artist: str | None, verbose: bool
) -> str:
    if not candidates:
        die(
            "no results found. Try a more specific query, e.g. "
            '"Album Name by Artist" --list'
        )
    playlists = [c for c in candidates if c.is_playlist]
    if playlists and playlists[0].score >= 20:
        best = playlists[0]
    else:
        full_videos = [
            c
            for c in candidates
            if not c.is_playlist
            and c.score >= 20
            and (c.duration is None or c.duration >= VIDEO_DUR_MIN)
        ]
        if full_videos:
            best = full_videos[0]
        elif playlists:
            best = playlists[0]
        elif candidates:
            best = candidates[0]
        else:
            die("no usable results found; try --list to inspect candidates")
    if best.score < 20:
        print(
            f"ytalbum: warning: weak match (score {best.score}) for '{best.title}'; "
            "verify with --list or pass --playlist <URL>",
            file=sys.stderr,
        )
    kind = "playlist" if best.is_playlist else "video"
    print(f"Using {kind}: {best.title}  (score {best.score}, id {best.id})")
    if verbose:
        print(f"+ target {best.url}", file=sys.stderr)
    return best.url


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="ytalbum",
        description='Download albums from YouTube by name. Example: ytalbum "In Rainbows by Radiohead"',
    )
    p.add_argument("album", nargs="?", help='album query, e.g. "In Rainbows by Radiohead"')
    p.add_argument("--artist", help="artist name (alternative to 'Album by Artist' syntax)")
    p.add_argument("-o", "--output", default="downloads", help="output directory (default: ./downloads)")
    p.add_argument("--format", default="mp3", choices=["mp3", "m4a", "opus", "flac", "wav", "vorbis"],
                   help="audio format (default: mp3)")
    p.add_argument("--quality", default="320K", help="audio quality passed to yt-dlp (default: 320K)")
    p.add_argument("--list", action="store_true", help="list ranked search candidates and exit")
    p.add_argument("--playlist", metavar="URL_OR_ID", help="skip search; download this playlist/video URL or ID")
    p.add_argument("--items", metavar="RANGE", help="download only these tracks, e.g. 1-3 or 1,4,7")
    p.add_argument("--dry-run", action="store_true", help="show the yt-dlp command without downloading")
    p.add_argument("--search-count", type=int, default=25, help="max search results to inspect (default: 25)")
    p.add_argument("--keep-video", action="store_true", help="keep original video file after processing")
    p.add_argument("--cookies", metavar="FILE", help="Netscape cookie file for yt-dlp (age-restricted content)")
    p.add_argument("--cookies-from-browser", metavar="BROWSER",
                   help="load YouTube cookies from a browser, e.g. chromium, firefox (fixes bot checks)")
    p.add_argument("-E", "--extractor-args", metavar="ARGS", action="append", default=[],
                   help="extra extractor args passed to yt-dlp, e.g. -E 'youtube:fetch_pot=always' "
                        "(repeatable; see README for bot-check help)")
    p.add_argument("-v", "--verbose", action="store_true", help="show underlying yt-dlp commands")
    p.add_argument("--version", action="version", version=f"ytalbum {VERSION}")
    args = p.parse_args(argv)

    ytdlp = find_ytdlp()
    find_ffmpeg()

    target: str | None = None
    album, artist = "", None

    if args.playlist:
        pid = args.playlist
        if pid.startswith(("PL", "OLAK")):
            target = f"https://www.youtube.com/playlist?list={pid}"
        elif pid.startswith("http"):
            target = pid
        elif re.fullmatch(r"[\w-]{11}", pid):
            target = f"https://www.youtube.com/watch?v={pid}"
        else:
            die(f"cannot interpret --playlist value: {pid!r}")
        album = args.album or pid
        artist = args.artist
    else:
        if not args.album:
            p.error('provide an album query (e.g. "In Rainbows by Radiohead") or --playlist')
        album, artist = parse_album_query(args.album, args.artist)
        query = album + (f" {artist}" if artist else "")
        candidates = search_candidates(ytdlp, query, args.search_count, args.verbose)
        ranked = rank(candidates, album, artist)
        if args.list:
            print_candidates(ranked, album, artist)
            return 0
        target = pick_target(ranked, album, artist, args.verbose)

    outdir = Path(args.output).expanduser()
    if artist:
        outdir = outdir / slug(artist) / slug(album)
    else:
        outdir = outdir / slug(album)

    cmd = build_download_cmd(
        ytdlp,
        target,
        outdir,
        args.format,
        args.quality,
        args.items,
        args.cookies,
        args.cookies_from_browser,
        args.extractor_args,
        args.keep_video,
        args.verbose,
        extra=[],
    )

    if args.dry_run:
        outdir.mkdir(parents=True, exist_ok=True)
        print(f"Would download to: {outdir}")
        print(" ".join(f"'{c}'" if " " in c else c for c in cmd))
        return 0

    outdir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading to: {outdir}")
    if args.verbose:
        print(f"+ {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(
            "ytalbum: hint: if YouTube asked you to sign in ('not a bot' error), retry with\n"
            "  --cookies-from-browser <chromium|firefox|brave>   (needs a logged-in browser profile)\n"
            "and/or a PO-token provider, e.g. bgutil-ytdlp-pot-provider with Deno/Node:\n"
            "  ytalbum ... -E 'youtube:fetch_pot=always'\n"
            "See README section 'Bot checks' for details.",
            file=sys.stderr,
        )
        die(f"yt-dlp exited with status {proc.returncode}")
    print(f"Done: {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
