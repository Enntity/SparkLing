# SPDX-License-Identifier: AGPL-3.0-only
"""Require the public SparkModelBench scorecard for the current product version."""
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseBenchmark(unittest.TestCase):
    def test_current_release_has_a_versioned_scorecard(self):
        version = json.loads((ROOT / "install/release.json").read_text())["version"]
        bundle = ROOT / "results" / f"sparkmodelbench-v{version}"
        path = bundle / "CARD.md"
        self.assertTrue(path.is_file(), f"Run bench/run.sh and publish {path.relative_to(ROOT)}")
        card = path.read_text()
        self.assertIn(f"# SparkLing v{version} · SparkModelBench\n", card.split("## ")[0])
        sections = {}
        for section in card.split("\n## ")[1:]:
            heading, _, body = section.partition("\n")
            sections[heading] = body.splitlines()
        for heading in ("RigMark Quality · task completion", "RigMark · generation, median",
                        "SparkLing · staggered C4", "RigMark · prefill", "RigMark · concurrency"):
            with self.subTest(heading=heading):
                rows = [line for line in sections.get(heading, []) if line.startswith("|")]
                self.assertGreater(len(rows), 2, f"Missing measured rows for {heading}")

    def test_published_files_match_their_checksums(self):
        version = json.loads((ROOT / "install/release.json").read_text())["version"]
        bundle = ROOT / "results" / f"sparkmodelbench-v{version}"
        listed = dict(reversed(line.split("  ", 1)) for line in (bundle / "SHA256SUMS").read_text().splitlines())
        self.assertIn("CARD.md", listed)
        for name, digest in listed.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((bundle / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
