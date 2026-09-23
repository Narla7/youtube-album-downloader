# ytalbum

Download albums from YouTube by name, powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

```bash
ytalbum "In Rainbows by Radiohead"
```

Finds the best-matching YouTube **playlist** for the album, downloads every track,
converts to MP3 (320K by default) and embeds metadata + cover art.

## Requirements

- Python 3.9+
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) on your `PATH`
- [`ffmpeg`](https://ffmpeg.org/) on your `PATH` (conversion / tagging / thumbnails)

## Install

```bash
# from a clone of this repo
uv tool install .        # or: pipx install .  /  pip install .

# or run without installing
./ytalbum.py --help
```

## Usage

```bash
# album + artist in one string
ytalbum "In Rainbows by Radiohead"

# or pass the artist separately
ytalbum "In Rainbows" --artist Radiohead

# preview which playlist/video would be chosen, ranked by score
ytalbum "In Rainbows by Radiohead" --list

# skip the search, download a specific playlist (URL or ID)
ytalbum --playlist https://www.youtube.com/playlist?list=OLAK5uy_...
ytalbum --playlist OLAK5uy_...

# only some tracks
ytalbum "In Rainbows by Radiohead" --items 1-3

# different format / quality / destination
ytalbum "In Rainbows by Radiohead" --format opus -o ~/Music

# pass raw extractor args through to yt-dlp (repeatable)
ytalbum "In Rainbows by Radiohead" -E 'youtube:fetch_pot=always'

# show the yt-dlp command without downloading
ytalbum "In Rainbows by Radiohead" --dry-run
```

## Bot checks ("Sign in to confirm you're not a bot")

YouTube sometimes flags an IP/network and refuses media extraction. `ytalbum`
surfaces a hint when this happens. Workarounds, in order of effort:

1. **Browser cookies** (usually enough on a normal home network):
   ```bash
   ytalbum "In Rainbows by Radiohead" --cookies-from-browser chromium
   # or: --cookies-from-browser firefox|brave|chrome, or --cookies cookies.txt
   ```
   The browser profile must be logged in to YouTube.
2. **PO-token provider** for persistently flagged IPs: install
   [`bgutil-ytdlp-pot-provider`](https://github.com/Brainicism/bgutil-ytdlp-pot-provider)
   into the same environment as yt-dlp, have Node.js ≥ 22 or Deno ≥ 2 available,
   then:
   ```bash
   ytalbum "In Rainbows by Radiohead" --cookies-from-browser chromium \
       -E 'youtube:fetch_pot=always'
   ```
3. Combine both if either alone fails.

### How selection works

1. Searches YouTube for `"Album Artist full album"` (playlist results included).
2. Scores every candidate: exact album/artist title matches, official YouTube
   Music album playlists (`OLAK...`), full-album videos; penalizes disc 2,
   lyric videos, best-ofs, commentary, etc.
3. Downloads the top-ranked playlist (falls back to a single full-album video).

Inspect the ranking with `--list`; override with `--playlist`.

### Development

```bash
python3 -m unittest test_ytalbum -v   # 19 unit tests, stdlib only
```

### Output layout

```
downloads/
└── Radiohead/
    └── In Rainbows/
        ├── 01 - 15 Step.mp3
        ├── 02 - Bodysnatchers.mp3
        └── ...
```

## License

MIT
