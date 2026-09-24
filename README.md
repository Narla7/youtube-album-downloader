# ytalbum — Download Albums from YouTube by Name

`ytalbum` is a tiny, dependency-free Python CLI that turns an album name into a
tagged audio library on your disk. Type what you know:

```bash
ytalbum "In Rainbows by Radiohead"
```

and get:

```text
downloads/
└── Radiohead/
    └── In Rainbows/
        ├── 01 - 15 Step.mp3
        ├── 02 - Bodysnatchers.mp3
        ├── 03 - Nude.mp3
        └── ...
```

with ID3 metadata and cover art embedded — album art is on **by default**, and
`--no-album-art` opts out. It is powered by
[yt-dlp](https://github.com/yt-dlp/yt-dlp) and
[ffmpeg](https://ffmpeg.org/) — `ytalbum` itself is stdlib-only Python and just
drives those tools intelligently.

> **Version:** 0.1.0 · **Python:** ≥ 3.9 · **License:** MIT
> **Repo:** <https://github.com/Narla7/youtube-album-downloader>

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Basic forms](#basic-forms)
  - [Inspecting results](#inspecting-results)
  - [Downloading specific playlists or videos](#downloading-specific-playlists-or-videos)
  - [Formats, quality, and destination](#formats-quality-and-destination)
  - [Partial downloads](#partial-downloads)
  - [Authentication and bot checks](#authentication-and-bot-checks)
  - [Advanced passthrough](#advanced-passthrough)
- [CLI Reference](#cli-reference)
- [Selection and Scoring in Detail](#selection-and-scoring-in-detail)
- [Output Layout and File Naming](#output-layout-and-file-naming)
- [Examples](#examples)
- [Bot Checks ("Sign in to confirm you're not a bot")](#bot-checks-sign-in-to-confirm-youre-not-a-bot)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Development](#development)
- [Project Structure](#project-structure)
- [Limitations and Legal Notes](#limitations-and-legal-notes)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Natural input:** `"In Rainbows by Radiohead"`, `"In_Rainbows by Radiohead"`,
  or `"In Rainbows" --artist Radiohead` all work. Case-insensitive `by`
  splitting, underscores converted to spaces.
- **Playlist-first search:** queries the YouTube results page directly (not the
  `ytsearch:` prefix) so **playlists are included**, not just videos.
- **Smart ranking:** official YouTube Music auto-generated album playlists
  (`OLAK…` IDs) are preferred; exact album/artist title matches score highest;
  Disc 2 variants, lyric videos, best-ofs, commentary/reaction videos, and live
  basement sessions are penalized. See
  [Selection and Scoring](#selection-and-scoring-in-detail).
- **Sensible fallback:** if no good playlist exists, a single long
  "full album" video (≥ 25 min) is used instead — with a warning when the match
  is weak (score < 20).
- **One-shot audio pipeline:** `yt-dlp -x --audio-format … --audio-quality …`
  plus `--embed-metadata --embed-thumbnail`, 4 concurrent fragments.
- **Album art by default:** every download passes `--embed-thumbnail`, so the
  video thumbnail is converted webp→png by ffmpeg and embedded into each audio
  file. New in 0.2.0: opt out per-run with `--no-album-art`.
- **Inspectable:** `--list` shows the ranked table with scores; `--dry-run`
  prints the exact `yt-dlp` command without downloading; `-v` echoes
  everything.
- **Override anything:** `--playlist <URL|PL…|OLAK…|video-ID>` skips search;
  `--items` limits tracks; `-E/--extractor-args` forwards anything to yt-dlp.
- **Bot-check aware:** `--cookies`, `--cookies-from-browser`, extractor-arg
  passthrough, and a helpful hint printed on failure.
- **Zero Python dependencies:** only the standard library. You just need the
  `yt-dlp` and `ffmpeg` binaries.

---

## How It Works

```text
  "In Rainbows by Radiohead"
            │
            ▼
  ┌─────────────────────┐
  │ 1. Parse query       │  split on " by " (case-insensitive),
  │                      │  "_" → " ", strip illegal filename chars
  └─────────┬───────────┘
            ▼
  ┌─────────────────────┐
  │ 2. Search YouTube    │  https://www.youtube.com/results?search_query=
  │                      │  "<Album> <Artist> full album", --flat-playlist,
  │                      │  up to --search-count entries (default 25)
  └─────────┬───────────┘
            ▼
  ┌─────────────────────┐
  │ 3. Filter + score    │  drop channels/radios/mixes (UC/RD/TL…),
  │                      │  score playlists and videos (see scoring table)
  └─────────┬───────────┘
            ▼
  ┌─────────────────────┐
  │ 4. Pick target       │  best playlist (score ≥ 20), else best full-length
  │                      │  video, else best playlist anyway, else best item;
  │                      │  warn if score < 20
  └─────────┬───────────┘
            ▼
  ┌─────────────────────┐
  │ 5. Download + tag    │  yt-dlp -x --audio-format mp3 --audio-quality 320K
  │                      │  --embed-metadata --embed-thumbnail   (album art
  │                      │  on by default; omit with --no-album-art)
  │                      │  -o "<out>/<Artist>/<Album>/NN - title.ext"
  └─────────────────────┘
```

---

## Requirements

| Tool       | Minimum      | Why                                    | Check               |
| ---------- | ------------ | -------------------------------------- | ------------------- |
| Python     | 3.9+         | runs `ytalbum.py` (uses `X \| Y` types) | `python3 --version` |
| `yt-dlp`   | recent (2024+) | search, download, convert            | `yt-dlp --version`  |
| `ffmpeg`   | any recent   | audio conversion, tagging, album-art   | `ffmpeg -version`   |
|            |              | embedding (webp→png thumbnails)        |                     |

`ytalbum` warns (but continues) if `ffmpeg` is missing; audio conversion,
tagging, and thumbnail embedding will then fail inside `yt-dlp`. It aborts with
a clear error if `yt-dlp` is not on `PATH`.

Optional, for hostile networks:

| Tool                              | When you need it                          |
| --------------------------------- | ----------------------------------------- |
| A Chromium/Firefox-based browser  | `--cookies-from-browser` bot-check bypass |
| Node.js ≥ 22 **or** Deno ≥ 2      | PO-token generation via bgutil provider   |
| `bgutil-ytdlp-pot-provider`       | persistently flagged IPs (see below)      |

---

## Installation

### Option A — install as a tool (recommended)

```bash
git clone https://github.com/Narla7/youtube-album-downloader.git
cd youtube-album-downloader

uv tool install .     # preferred
# or:
pipx install .        # alternative isolated install
pip install .         # plain install into current env
```

This exposes the `ytalbum` command (see `pyproject.toml`
`[project.scripts]`). Verify:

```bash
ytalbum --version   # ytalbum 0.1.0
ytalbum --help
```

### Option B — run without installing

```bash
git clone https://github.com/Narla7/youtube-album-downloader.git
cd youtube-album-downloader
chmod +x ytalbum.py
./ytalbum.py --help
# or: python3 ytalbum.py --help
```

### Option C — one-liner test drive

```bash
git clone --depth 1 https://github.com/Narla7/youtube-album-downloader.git \
  && cd youtube-album-downloader \
  && ./ytalbum.py "In Rainbows by Radiohead" --list
```

`--list` only searches and prints the ranking — nothing is downloaded.

### Updating

```bash
cd youtube-album-downloader
git pull
uv tool install . --force   # if installed via uv tool
yt-dlp -U                   # keep yt-dlp itself current (important!)
```

---

## Quick Start

```bash
# 1. Check prerequisites
python3 --version && yt-dlp --version && ffmpeg -version | head -n1

# 2. See what would be downloaded (free, fast, no audio fetched)
ytalbum "In Rainbows by Radiohead" --list

# 3. Dry run — show destination + exact yt-dlp command
ytalbum "In Rainbows by Radiohead" --dry-run

# 4. Download for real
ytalbum "In Rainbows by Radiohead"
```

---

## Usage

### Basic forms

All of these download the same album:

```bash
ytalbum "In Rainbows by Radiohead"
ytalbum "In_Rainbows by Radiohead"      # underscores → spaces
ytalbum "IN RAINBOWS BY RADIOHEAD"      # case-insensitive
ytalbum "In Rainbows" --artist Radiohead
```

Album-only queries work too (folder will lack the artist level):

```bash
ytalbum "In Rainbows"
```

### Inspecting results

```bash
# Ranked table of playlists + videos with scores — nothing downloaded
ytalbum "In Rainbows by Radiohead" --list

# Sample output:
# Search results for: In Rainbows by Radiohead
#   #  TYPE      SCORE  ID                       TITLE
#   1  playlist    110  OLAK5uy_lvqkQRb8iVo2ob…  In Rainbows
#   2  playlist     95  PLpuAQIiG6Znp_SRcaF-mJ…  Radiohead - In Rainbows [Full Album]
#  ...

# Inspect even more candidates (default 25)
ytalbum "In Rainbows by Radiohead" --list --search-count 50

# Show the full yt-dlp command + destination, download nothing
ytalbum "In Rainbows by Radiohead" --dry-run

# Verbose: echo every underlying yt-dlp invocation to stderr
ytalbum "In Rainbows by Radiohead" --dry-run -v
```

### Downloading specific playlists or videos

Skip the search entirely when you already know the target:

```bash
# Full playlist URL
ytalbum --playlist "https://www.youtube.com/playlist?list=OLAK5uy_..."

# Bare playlist ID (PL… user playlists, OLAK… official album playlists)
ytalbum --playlist OLAK5uy_...
ytalbum --playlist PLpuAQIiG6Znp_SRcaF-mJ8q1ef-7yeHtO

# Single video URL or 11-char video ID (downloaded as one file)
ytalbum --playlist "https://www.youtube.com/watch?v=m3z317k9HlI"
ytalbum --playlist m3z317k9HlI

# Combine with a label for nicer folder naming
ytalbum "In Rainbows" --artist Radiohead --playlist OLAK5uy_...
```

`ytalbum` accepts any `http…` target verbatim and converts bare `PL…`/`OLAK…`
IDs to `https://www.youtube.com/playlist?list=<ID>` and bare 11-character IDs
to `https://www.youtube.com/watch?v=<ID>`. Anything else is rejected with
`cannot interpret --playlist value`.

### Formats, quality, and destination

```bash
# Audio format (default mp3). Choices: mp3 m4a opus flac wav vorbis
ytalbum "In Rainbows by Radiohead" --format opus
ytalbum "In Rainbows by Radiohead" --format flac

# Quality string passed straight to yt-dlp --audio-quality (default 320K)
ytalbum "In Rainbows by Radiohead" --quality 320K
ytalbum "In Rainbows by Radiohead" --format opus --quality 160K

# Destination root (default ./downloads). ~ is expanded.
ytalbum "In Rainbows by Radiohead" -o ~/Music
ytalbum "In Rainbows by Radiohead" --output /mnt/nas/audio

# Keep the original video file too (default: audio only via -x)
ytalbum "In Rainbows by Radiohead" --keep-video

# Album art is embedded by default (--embed-thumbnail); opt out if the
# uploader's thumbnail isn't the real cover, or if you tag art yourself
ytalbum "In Rainbows by Radiohead" --no-album-art
```

### Partial downloads

`--items` maps to yt-dlp's `--playlist-items`:

```bash
ytalbum "In Rainbows by Radiohead" --items 1-3     # first three tracks
ytalbum "In Rainbows by Radiohead" --items 1,4,7   # specific tracks
ytalbum "In Rainbows by Radiohead" --items 5:      # track 5 to the end
```

Handy for testing your setup with a single track (`--items 1`) before
committing to a full discography.

### Authentication and bot checks

```bash
# Use cookies from a logged-in browser profile (must be logged into YouTube)
ytalbum "In Rainbows by Radiohead" --cookies-from-browser chromium
ytalbum "In Rainbows by Radiohead" --cookies-from-browser firefox

# Or a Netscape-format cookie file
ytalbum "In Rainbows by Radiohead" --cookies cookies.txt
```

### Advanced passthrough

`-E/--extractor-args` is repeatable and forwarded verbatim as
`--extractor-args` to yt-dlp — for both the search and the download:

```bash
# Force PO-token minting (needs a PO-token provider installed, see below)
ytalbum "In Rainbows by Radiohead" -E 'youtube:fetch_pot=always'

# Pin the player client
ytalbum "In Rainbows by Radiohead" -E 'youtube:player_client=web'

# Combine several
ytalbum "In Rainbows by Radiohead" \
  --cookies-from-browser chromium \
  -E 'youtube:fetch_pot=always' \
  -E 'youtube:player_client=web'
```

---

## CLI Reference

```text
usage: ytalbum [-h] [--artist ARTIST] [-o OUTPUT]
               [--format {mp3,m4a,opus,flac,wav,vorbis}] [--quality QUALITY]
               [--list] [--playlist URL_OR_ID] [--items RANGE] [--dry-run]
               [--search-count SEARCH_COUNT] [--keep-video] [--no-album-art]
               [--cookies FILE] [--cookies-from-browser BROWSER] [-E ARGS]
               [-v] [--version]
               [album]
```

| Argument                   | Default      | Description                                                        |
| -------------------------- | ------------ | ------------------------------------------------------------------ |
| `album`                    | —            | Album query, e.g. `"In Rainbows by Radiohead"`. Optional if `--playlist` is given. |
| `--artist ARTIST`          | —            | Artist name; alternative to the `"Album by Artist"` syntax. Explicit flag wins. |
| `-o, --output DIR`         | `downloads`  | Destination root (`~` expanded). Final path is `<DIR>/<Artist>/<Album>/`, or `<DIR>/<Album>/` when no artist is known. |
| `--format FMT`             | `mp3`        | Audio format: `mp3`, `m4a`, `opus`, `flac`, `wav`, `vorbis`. Passed as yt-dlp `--audio-format`. |
| `--quality Q`              | `320K`       | Audio quality string, forwarded as yt-dlp `--audio-quality`.       |
| `--list`                   | off          | Rank candidates and exit. Downloads nothing.                       |
| `--playlist URL_OR_ID`     | —            | Skip search. Accepts playlist/video URL, `PL…`/`OLAK…` ID, or 11-char video ID. |
| `--items RANGE`            | —            | Track subset, e.g. `1-3`, `1,4,7`. Forwarded as `--playlist-items`. |
| `--dry-run`                | off          | Create the destination, print the yt-dlp command, download nothing. |
| `--search-count N`         | `25`         | Max search-result entries to fetch and rank (`--playlist-end`).    |
| `--keep-video`             | off          | Keep the source video (omit yt-dlp `-x`).                          |
| `--no-album-art`           | off          | Drop yt-dlp `--embed-thumbnail` so nothing is embedded as cover art. Files are still tagged (see `--embed-metadata`); when off (default), the video thumbnail is embedded as album art. |
| `--cookies FILE`           | —            | Netscape cookie file, forwarded as `--cookies`.                    |
| `--cookies-from-browser B` | —            | Browser name (`chromium`, `firefox`, `brave`, …), forwarded as `--cookies-from-browser`. |
| `-E, --extractor-args A`   | —            | Repeatable. Forwarded verbatim as `--extractor-args`.              |
| `-v, --verbose`            | off          | Echo underlying yt-dlp commands; also passes `--verbose` to yt-dlp. |
| `--version`                | —            | Print `ytalbum <VERSION>` and exit.                                |

Exit codes: `0` on success; `1` on any error (missing tools, empty query,
search failure, yt-dlp non-zero exit, uninterpretable `--playlist`).

---

## Selection and Scoring in Detail

### Search

`ytalbum` fetches
`https://www.youtube.com/results?search_query=<Album>+<Artist>+full+album`
with `yt-dlp --flat-playlist --print "%(ie_key)s\t%(id)s\t%(duration)s\t%(title)s"`.
The plain results URL (deliberately **not** the `ytsearch:` prefix) returns
**playlists mixed with videos**. Entries starting with `UC/RD/TL/UUK`
(channels, radios, mixes) are discarded; `PL…`/`OLAK…` count as playlists.

### Scoring

Each candidate starts at 0. Applied in order:

| Rule                                                        | Playlists | Videos |
| ----------------------------------------------------------- | :-------: | :----: |
| ID starts with `OLAK` (official YouTube Music album)        |   +60     |   —    |
| Title contains `"full album"`                               |   +15     |  +20   |
| Title contains `"album"` (but not "full album")             |    —      |   +8   |
| Duration ≥ 1500 s (25 min, full-length)                     |    —      |  +10   |
| Duration < 600 s (single track, unlikely the album)         |    —      |  −30   |
| Title contains the album name (substring, case-insensitive) |   +50     |  +50   |
| Title contains the artist name                              |   +30     |  +30   |
| `disc/disk/cd 2`                                            |   −50     |  −50   |
| `"lyrics"`                                                  |   −40     |  −40   |
| `"best of"` / `"greatest"` / `"hits"`                       |   −50     |  −50   |
| `"commentary"` / `"interview"` / `"reaction"`               |   −50     |  −50   |
| `"from the basement"` / `"scotch mist"` / `"live at"`       |   −25     |  −25   |

Ranking sorts playlists first (by score, descending), then videos.

### Picking (`pick_target`)

1. If the best playlist scores **≥ 20** → use it.
2. Else, if a video scores **≥ 20** and is long (≥ 1500 s, or unknown
   duration) → use the best such video as a single-file album.
3. Else, fall back to the best playlist, or the best item overall.
4. If the winner scores **< 20**, a `weak match` warning is printed to stderr
   suggesting `--list` or `--playlist`.

### Concrete example

For `"In Rainbows by Radiohead"` a typical ranking is:

| # | Type     | Score | ID | Why                                     |
| - | -------- | ----: | -- | --------------------------------------- |
| 1 | playlist |   110 | `OLAK5uy_…` | official album (+60) + album in title (+50) |
| 2 | playlist |    95 | `PLpuAQ…`  | album (+50) + artist (+30) + full album (+15) |
| … | playlist |    45 | `PL…Disk 2…` | same as above, minus 50 for disc 2 |
| … | video    |   −40 | `…` | lyric video penalty                     |

---

## Output Layout and File Naming

- Root: `--output` (default `./downloads`), created with `mkdir -p`.
- With artist: `<root>/<Artist>/<Album>/`. Without: `<root>/<Album>/`.
- Folder names are sanitized: `< > : " / \ | ? *` and control chars removed.
- Playlist tracks: `%(playlist_index)02d - %(title)s.%(ext)s`
  (e.g. `01 - 15 Step.mp3`). Single videos: `%(title)s.%(ext)s`.
- Every download runs with `--embed-metadata --embed-thumbnail` and
  `--concurrent-fragments 4`. Audio extraction uses `-x` unless
  `--keep-video` is given.
- **Album art is embedded by default.** yt-dlp downloads the video thumbnail,
  converts it webp→png via ffmpeg, and embeds it into each audio file — an MP3
  ends up with a 1280×1280 attached PNG picture stream. Pass `--no-album-art`
  to drop `--embed-thumbnail` from the yt-dlp command, so files are tagged
  with metadata but carry no embedded cover.
- Re-running is cheap: yt-dlp skips files that already exist.

---

## Examples

```bash
# The classic
ytalbum "In Rainbows by Radiohead"

# Non-English names, special chars are sanitized for the filesystem
ytalbum "Ágætis byrjun by Sigur Rós" -o ~/Music

# Jazz box set, lossless, only discs you want (after --list inspection)
ytalbum "Kind of Blue by Miles Davis" --format flac --items 1-5

# Force the official YouTube Music tracklist when search is noisy
ytalbum "In Rainbows" --artist Radiohead --playlist OLAK5uy_lvqkQRb8iVo2obChPXi9XFRLoIyaxbTj8

# Same, but skip embedded cover art (tags only)
ytalbum "In Rainbows" --artist Radiohead --playlist OLAK5uy_lvqkQRb8iVo2obChPXi9XFRLoIyaxbTj8 --no-album-art

# Scripting: exact command preview is machine-parseable via --dry-run
ytalbum "In Rainbows by Radiohead" --dry-run -o /tmp/stage --items 1

# Full debug transcript
ytalbum "In Rainbows by Radiohead" -v --items 1 2>debug.log
```

---

## Bot Checks ("Sign in to confirm you're not a bot")

YouTube flags some IPs/networks (datacenters, VPN exits, rotating IPv6,
high-volume scrapers) and refuses **media** requests even though search and
metadata still work. Symptoms: `yt-dlp` exits non-zero with
`Sign in to confirm you're not a bot`, and `ytalbum` prints its hint block.

This is environmental, not an app bug. Escalate in this order:

### 1. Use a residential IP

Home broadband almost always works with no extra steps. If you're on a
VPS/VPN/Tor exit, try off it first. Forcing IPv4 sometimes helps on
tunnel-broken IPv6:

```bash
ytalbum "In Rainbows by Radiohead" -E 'youtube:prefer_ipv4=true'
```

### 2. Pass a logged-in browser session

```bash
ytalbum "In Rainbows by Radiohead" --cookies-from-browser chromium
# firefox | brave | chrome | edge | opera | vivaldi also accepted by yt-dlp
```

Requirements: the profile must exist locally **and be logged into YouTube**;
headless/encrypted cookie stores yt-dlp can't decrypt won't help. Or export a
Netscape file from a browser extension and use `--cookies cookies.txt`.
Keep `yt-dlp` current (`yt-dlp -U`) — bot-check handling improves monthly.

### 3. Add a PO-token provider (persistently flagged IPs)

[PO tokens](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) prove a real
player ran the request. The community standard is
[`bgutil-ytdlp-pot-provider`](https://github.com/Brainicism/bgutil-ytdlp-pot-provider):

```bash
# into the SAME environment as yt-dlp (example with a venv):
uv venv ~/.venvs/yt && uv pip install --python ~/.venvs/yt/bin/python \
  yt-dlp bgutil-ytdlp-pot-provider

# provider's JS runtime (either):
#   Node.js >= 22  →  npm ci && npx tsc  in bgutil-ytdlp-pot-provider/server/
#   Deno >= 2      →  usable directly via the generate_once.ts script

# then:
ytalbum "In Rainbows by Radiohead" --cookies-from-browser chromium \
  -E 'youtube:fetch_pot=always'
```

Combinations that were verified during development (yt-dlp 2026.08.19):

| Setup | Result on flagged IP |
| ----- | -------------------- |
| bare `yt-dlp`, any `player_client` | `LOGIN_REQUIRED` bot error |
| `+ --cookies-from-browser` (undecryptable store) | still blocked |
| `+ bgutil script provider`, `fetch_pot=always` | token minted, player API reached, still `LOGIN_REQUIRED` without a valid login session |
| residential IP + cookies | works |

Takeaway: PO tokens help, but on a hard-flagged IP you still need **both** a
valid login session **and** tokens. There is no supported flag-free bypass —
that would be breaking YouTube's bot protection.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| `yt-dlp not found on PATH` | dependency missing | install yt-dlp, ensure it is on `PATH` |
| `ffmpeg not found` warning + convert failure | dependency missing | install ffmpeg |
| `yt-dlp search failed` | network down / YouTube layout change | check connectivity; `yt-dlp -U`; retry with `-v` |
| `(no results)` from `--list` | query too obscure / `--search-count` too low | quote `"Album by Artist"`, raise `--search-count 50` |
| `weak match (score …)` warning | noisy search results | inspect `--list`, then pin with `--playlist` |
| `cannot interpret --playlist value` | typo'd ID | pass full URL, `PL…`/`OLAK…`, or 11-char video ID |
| `Sign in to confirm you're not a bot` | flagged IP / no session | see [Bot Checks](#bot-checks-sign-in-to-confirm-youre-not-a-bot) |
| `ERROR: … cookies … no key found` | encrypted browser store yt-dlp can't read | use `--cookies cookies.txt` export instead |
| No album art in the audio files | `--no-album-art` was passed, or ffmpeg is missing so yt-dlp's thumbnail conversion/embed failed | drop the flag; install ffmpeg (watch the startup warning) |
| Wrong album downloaded | ambiguous title (many same-name albums) | always include `--artist`; verify with `--list` first |
| Files named `NA - …` | playlist lacks indices (rare) | use `--playlist` with a proper playlist; or accept video titles |
| `Downloads are slow` | default fragment concurrency | it already uses `--concurrent-fragments 4`; check your link |

Run anything with `-v` for the full underlying command transcript.

---

## FAQ

**Does it download video?**
No, by default. `-x` extracts audio only. Pass `--keep-video` to also keep
the source video file.

**MP3 320K from a lossy YouTube stream — pointless?**
YouTube audio is Opus/AAC ~128–160K. Transcoding to MP3 320K doesn't restore
quality, but MP3 is the compatible default (car stereos, old players). If you
care about fidelity-per-byte, use `--format opus`. If you want archival,
`--format flac` (still transcoded, but lossless container).

**Why playlists instead of one "full album" video?**
Per-track files get proper indices, titles, and embedded tags; a single video
gives you one 60-minute blob. You can still force the blob with `--playlist
<video-URL>`.

**Can I skip the embedded album art?**
Yes — `--no-album-art`. Cover art (the video thumbnail, embedded as a
1280×1280 PNG picture stream in MP3s) is on by default. Opt out when the
uploader's thumbnail isn't the real artwork, or when you tag cover art
yourself afterward.

**Why does search need no API key?**
It scrapes the public YouTube results page through yt-dlp's flat-playlist
mode — no API quota, no key.

**Does it support Spotify/Apple Music lookups?**
No. Input is an album name; resolution is YouTube-only by design.

**Can I script it?**
Yes: `--dry-run` prints the destination line + exact command; exit codes are
`0`/`1`; `--list` output is stable text. `--playlist` makes runs
deterministic (no search involved).

**Is downloading from YouTube legal?**
Downloading violates YouTube's Terms of Service (except where they offer an
explicit download button). Copyright in the music stays with its owners, so
**do not redistribute** what you download. Personal, local use is the intended
scope of this tool. (Not legal advice.)

---

## Development

```bash
git clone https://github.com/Narla7/youtube-album-downloader.git
cd youtube-album-downloader

# run the suite (stdlib unittest, no third-party test deps)
python3 -m unittest test_ytalbum -v   # 22 tests

# style: keep it stdlib-only, argparse-based, one module
python3 -m py_compile ytalbum.py test_ytalbum.py
```

Test coverage includes: query parsing (`by` splitting, underscores, artist
flag, empty input), filename sanitizing, ranking/scoring rules (official
playlist preference, disc-2/lyrics penalties, playlist-before-video),
target picking (playlist preference, full-video fallback, empty error), URL
building, and download-command construction (playlist vs video flags,
auth/extractor-arg forwarding, `--embed-thumbnail` present by default,
omitted with `album_art=False`, present with `album_art=True`).

---

## Project Structure

```text
youtube-album-downloader/
├── ytalbum.py        # the CLI — parsing, search, scoring, download (stdlib only)
├── test_ytalbum.py   # 22 stdlib unit tests for the pure functions
├── pyproject.toml    # setuptools build; exposes the `ytalbum` entry point
├── flake.nix         # Nix flake: package, app, devShell, and test check
├── README.md         # this file
├── LICENSE           # MIT
└── .gitignore        # caches, build output, downloads/
```

`ytalbum.py` is intentionally a single module: `Candidate` dataclass +
`parse_album_query / build_search_url / search_candidates / score_candidate /
rank / print_candidates / pick_target / build_download_cmd / main`,
with `album_art: bool = True` controlling `--embed-thumbnail`.

---

## Limitations and Legal Notes

- Results depend on what uploaders publish; unofficial uploads can have wrong
  tags, crowd noise, or gaps. Verify with `--list`.
- Auto-generated (`OLAK…`) playlists are usually the clean studio tracklist —
  preferred automatically when they match.
- Album art comes from the video thumbnail — on re-uploads that may be nothing
  like the real cover. Use `--no-album-art` and tag your own art if that
  matters.
- Single-video fallback has no per-track splits (use `--items` only with
  playlists).
- No SponsorBlock, no chapter splitting, no lyrics fetching (out of scope).
- YouTube's layout and bot protection change often: if search breaks, update
  yt-dlp first (`yt-dlp -U`), then file an issue with `-v` output.
- Respect copyright and YouTube's ToS. This tool is for personal local use;
  redistribution of downloaded content may infringe copyright.

---

## Changelog

### 0.2.0 — album art control (unreleased)

- Album art is now embedded **by default**: every download passes
  `--embed-thumbnail` to yt-dlp, which fetches the video thumbnail, converts
  it webp→png via ffmpeg, and attaches it to the audio files (MP3s carry a
  1280×1280 attached PNG picture stream).
- New `--no-album-art` flag: an opt-out that removes `--embed-thumbnail` from
  the yt-dlp command, so files are still tagged (ID3 metadata) but carry no
  embedded cover.
- `build_download_cmd` gained the keyword parameter `album_art: bool = True`;
  `main` wires it as `album_art=not args.no_album_art`.
- Test suite now counts **22 tests** (was 19): `--embed-thumbnail` present by
  default, omitted with `album_art=False`, included with `album_art=True`.

### 0.1.0 — initial release

- `"Album by Artist"` query parsing (case-insensitive `by`, `_` → space).
- YouTube results-page search returning playlists + videos.
- Score-based ranking with official-album preference and junk penalties.
- Playlist download as indexed audio files; single-video fallback.
- MP3 320K default with metadata + thumbnail embedding.
- `--list`, `--dry-run`, `--playlist`, `--items`, `--cookies*`,
  `-E/--extractor-args`, `--keep-video`, `-v`.
- Bot-check hint on failure.
- 19 stdlib unit tests.

---

## Contributing

Issues and PRs welcome:

1. Fork, branch (`feat/…` / `fix/…`), keep the stdlib-only rule.
2. Add/extend tests in `test_ytalbum.py` (`python3 -m unittest test_ytalbum -v`).
3. Update this README if flags or behavior change.
4. PR against `main` with `-v` sample output for behavior changes.

---

## License

MIT — see [LICENSE](LICENSE).