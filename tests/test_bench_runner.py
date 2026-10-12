"""bench_runner 的自动化测试：验证盲评防护机制确实生效。"""
import csv
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))

import bench_runner


def _quiet(fn, *args, **kwargs):
    """bench_runner 会向 stdout 打印进度，测试中静音以免淹没 CI 日志。"""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class BenchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.original_runs = bench_runner.RUNS
        self.original_scorecard = bench_runner.SCORECARD
        bench_runner.RUNS = self.tmp / "runs"
        bench_runner.SCORECARD = self.tmp / "scorecard.csv"

    def tearDown(self):
        bench_runner.RUNS = self.original_runs
        bench_runner.SCORECARD = self.original_scorecard
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _manifest(self, runs=1):
        manifest = _quiet(bench_runner.generate_manifest, salt="unittest", runs_per_config=runs)
        return manifest

    def test_generate_creates_expected_item_count(self):
        manifest = self._manifest(runs=2)
        self.assertEqual(len(manifest["entries"]), 4 * 3 * 2)

    def test_blinded_ids_are_unique(self):
        manifest = self._manifest(runs=2)
        ids = [e["blinded_id"] for e in manifest["entries"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_same_salt_is_reproducible(self):
        first = bench_runner.blind_id("B01", "A", "fixedsalt", 1)
        second = bench_runner.blind_id("B01", "A", "fixedsalt", 1)
        self.assertEqual(first, second)

    def test_run_index_changes_blinded_id(self):
        first = bench_runner.blind_id("B01", "A", "fixedsalt", 1)
        second = bench_runner.blind_id("B01", "A", "fixedsalt", 2)
        self.assertNotEqual(first, second)

    def test_config_not_leaked_in_review_order(self):
        self._manifest(runs=1)
        text = (bench_runner.RUNS / "review_order.txt").read_text(encoding="utf-8")
        for label in ("config_A", "config_B", "config_C", "plain", "skill", "rebuild_full"):
            self.assertNotIn(label, text)

    def test_reveal_requires_two_reviewers(self):
        manifest = self._manifest(runs=1)
        ids = [e["blinded_id"] for e in manifest["entries"]]
        self._write_review("review_1.csv", ids, "甲")
        _quiet(bench_runner.import_reviews, str(bench_runner.RUNS / "review_1.csv"))
        with self.assertRaises(SystemExit) as ctx:
            _quiet(bench_runner.reveal)
        self.assertIn("2 名独立评审", str(ctx.exception))

    def test_reveal_rejects_incomplete_coverage(self):
        manifest = self._manifest(runs=1)
        ids = [e["blinded_id"] for e in manifest["entries"]]
        self._write_review("r1.csv", ids, "甲")
        self._write_review("r2.csv", ids[:-2], "乙")
        _quiet(bench_runner.import_reviews, 
            str(bench_runner.RUNS / "r1.csv"), str(bench_runner.RUNS / "r2.csv")
        )
        with self.assertRaises(SystemExit) as ctx:
            _quiet(bench_runner.reveal)
        self.assertIn("未评完全部条目", str(ctx.exception))

    def test_reveal_succeeds_with_two_complete_reviewers(self):
        manifest = self._manifest(runs=1)
        ids = [e["blinded_id"] for e in manifest["entries"]]
        self._write_review("r1.csv", ids, "甲")
        self._write_review("r2.csv", ids, "乙")
        _quiet(bench_runner.import_reviews, 
            str(bench_runner.RUNS / "r1.csv"), str(bench_runner.RUNS / "r2.csv")
        )
        _quiet(bench_runner.reveal)
        self.assertTrue(bench_runner.SCORECARD.exists())
        with bench_runner.SCORECARD.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), len(ids) * 2)

    def test_import_rejects_missing_columns(self):
        path = bench_runner.RUNS / "bad.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("blinded_id,reviewer\nX-1,甲\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _quiet(bench_runner.import_reviews, str(path))
        self.assertIn("缺少字段", str(ctx.exception))

    def _write_review(self, name, ids, reviewer, score=3):
        bench_runner.RUNS.mkdir(parents=True, exist_ok=True)
        path = bench_runner.RUNS / name
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["blinded_id", "reviewer"] + bench_runner.RUBRIC_DIMENSIONS +
                ["total", "critical_failure_count", "notes"]
            )
            for blinded in ids:
                writer.writerow(
                    [blinded, reviewer] + [score] * 8 +
                    [score * 8, 0, ""]
                )
        return path


if __name__ == "__main__":
    unittest.main()
