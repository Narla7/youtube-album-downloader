#!/usr/bin/env python3
"""Unit tests for ytalbum (stdlib only: python3 -m unittest test_ytalbum -v)."""

import unittest
from pathlib import Path

import ytalbum
from ytalbum import Candidate, build_download_cmd, parse_album_query, pick_target, rank, slug


def cand(id_, title, duration=None):
    ie = "YoutubeTab" if id_.startswith(("PL", "OLAK")) else "Youtube"
    return Candidate(ie, id_, duration, title)


class TestParseAlbumQuery(unittest.TestCase):
    def test_album_by_artist(self):
        self.assertEqual(
            parse_album_query("In Rainbows by Radiohead", None),
            ("In Rainbows", "Radiohead"),
        )

    def test_underscores_become_spaces(self):
        album, artist = parse_album_query("In_Rainbows by Radiohead", None)
        self.assertEqual((album, artist), ("In Rainbows", "Radiohead"))

    def test_case_insensitive_by(self):
        self.assertEqual(
            parse_album_query("In Rainbows BY Radiohead", None),
            ("In Rainbows", "Radiohead"),
        )

    def test_artist_flag_wins(self):
        self.assertEqual(
            parse_album_query("In Rainbows", "Radiohead"),
            ("In Rainbows", "Radiohead"),
        )

    def test_album_only(self):
        self.assertEqual(parse_album_query("In Rainbows", None), ("In Rainbows", None))

    def test_empty_dies(self):
        with self.assertRaises(SystemExit):
            parse_album_query("   ", None)


class TestSlug(unittest.TestCase):
    def test_illegal_chars_stripped(self):
        self.assertEqual(slug('AC/DC: "Live" <2024>'), "ACDC Live 2024")

    def test_spaces_kept(self):
        self.assertEqual(slug("In Rainbows"), "In Rainbows")


class TestRanking(unittest.TestCase):
    def test_official_album_playlist_ranks_first(self):
        cs = [
            cand("PLxyz", "Radiohead - In Rainbows (Full Album)", None),
            cand("OLAK5uy_abc", "In Rainbows", None),
            cand("PLjunk", "Best of Radiohead Greatest Hits", None),
        ]
        ranked = rank(cs, "In Rainbows", "Radiohead")
        self.assertEqual(ranked[0].id, "OLAK5uy_abc")
        self.assertEqual([c.id for c in ranked][-1], "PLjunk")

    def test_disc2_penalized(self):
        cs = [
            cand("PLaaa", "Radiohead - In Rainbows Disk 2 (Full Album)", None),
            cand("PLbbb", "Radiohead - In Rainbows (Full Album)", None),
        ]
        ranked = rank(cs, "In Rainbows", "Radiohead")
        self.assertEqual(ranked[0].id, "PLbbb")

    def test_lyrics_penalized(self):
        cs = [
            cand("PLccc", "In Rainbows Full Album Lyrics", None),
            cand("PLddd", "In Rainbows (Full Album)", None),
        ]
        ranked = rank(cs, "In Rainbows", None)
        self.assertEqual(ranked[0].id, "PLddd")

    def test_playlists_before_videos(self):
        cs = [
            cand("dQw4w9WgXcQ", "Radiohead - In Rainbows Full Album", 3600),
            cand("PLeee", "Radiohead - In Rainbows (Full Album)", None),
        ]
        ranked = rank(cs, "In Rainbows", "Radiohead")
        self.assertTrue(ranked[0].is_playlist)


class TestPickTarget(unittest.TestCase):
    def test_empty_dies(self):
        with self.assertRaises(SystemExit):
            pick_target([], "In Rainbows", "Radiohead", False)

    def test_prefers_playlist(self):
        cs = rank(
            [
                cand("dQw4w9WgXcQ", "Radiohead - In Rainbows Full Album", 3600),
                cand("PLfff", "Radiohead - In Rainbows (Full Album)", None),
            ],
            "In Rainbows",
            "Radiohead",
        )
        url = pick_target(cs, "In Rainbows", "Radiohead", False)
        self.assertIn("list=PLfff", url)

    def test_falls_back_to_full_video(self):
        cs = rank(
            [cand("dQw4w9WgXcQ", "Radiohead - In Rainbows Full Album", 3600)],
            "In Rainbows",
            "Radiohead",
        )
        url = pick_target(cs, "In Rainbows", "Radiohead", False)
        self.assertIn("watch?v=dQw4w9WgXcQ", url)


class TestBuildDownloadCmd(unittest.TestCase):
    def test_playlist_cmd(self):
        cmd = build_download_cmd(
            "yt-dlp", "https://www.youtube.com/playlist?list=PLfff",
            Path("/tmp/x"), "mp3", "320K", None, None, None, [], False, False, [],
        )
        self.assertIn("--yes-playlist", cmd)
        self.assertIn("%(playlist_index)02d - %(title)s.%(ext)s", cmd)
        self.assertIn("-x", cmd)
        self.assertIn("--embed-thumbnail", cmd)
        self.assertEqual(cmd[-1], "https://www.youtube.com/playlist?list=PLfff")

    def test_video_cmd(self):
        cmd = build_download_cmd(
            "yt-dlp", "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            Path("/tmp/x"), "opus", "320K", None, None, None, [], False, False, [],
        )
        self.assertIn("--no-playlist", cmd)
        self.assertIn("--audio-format", cmd)
        self.assertIn("opus", cmd)

    def test_auth_and_extractor_args_forwarded(self):
        cmd = build_download_cmd(
            "yt-dlp", "https://www.youtube.com/playlist?list=PLfff",
            Path("/tmp/x"), "mp3", "320K", "1-3", "ck.txt", "chromium",
            ["youtube:fetch_pot=always"], False, False, [],
        )
        self.assertIn("--playlist-items", cmd)
        self.assertIn("1-3", cmd)
        self.assertIn("--cookies", cmd)
        self.assertIn("--cookies-from-browser", cmd)
        self.assertIn("--extractor-args", cmd)
        self.assertIn("youtube:fetch_pot=always", cmd)


class TestCandidate(unittest.TestCase):
    def test_urls(self):
        self.assertEqual(
            cand("PLfff", "t").url, "https://www.youtube.com/playlist?list=PLfff"
        )
        self.assertEqual(
            cand("dQw4w9WgXcQ", "t").url,
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )


if __name__ == "__main__":
    unittest.main()
