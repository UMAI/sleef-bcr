"""Regression checks for overlay synchronization; no network or Bazel required."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("prepare", Path(__file__).with_name("prepare.py"))
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        self.source.mkdir()
        self.git("init", "-q")
        (self.source / "upstream.txt").write_text("pinned upstream\n")
        (self.source / "config.txt").write_text("original configuration\n")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--no-gpg-sign", "-qm", "Upstream fixture")
        self.root = self.base / "overlay-repo"
        (self.root / "overlay" / "src" / "pkg").mkdir(parents=True)
        (self.root / "overlay" / "src" / "pkg" / "BUILD.bazel").write_text("# first\n")
        self.config = {"revision": self.git("rev-parse", "HEAD"),
                       "repository": "https://example.invalid/unused.git", "version": "test"}
        self.write_config()

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.source), *args], text=True,
        ).strip()

    def write_config(self):
        (self.root / "upstream.json").write_text(json.dumps(self.config))

    def prepare(self, **kwargs):
        return PREPARE.prepare(self.root, str(self.source), **kwargs)

    def test_exports_pinned_sources_without_modifying_source_checkout(self):
        (self.source / "upstream.txt").write_text("uncommitted edit\n")
        (self.source / "untracked.txt").write_text("not part of upstream\n")
        before = self.git("status", "--porcelain")
        workspace = self.prepare()
        self.assertEqual((workspace / "upstream.txt").read_text(), "pinned upstream\n")
        self.assertFalse((workspace / "untracked.txt").exists())
        self.assertEqual(self.git("status", "--porcelain"), before)

    def test_updates_removes_and_restores_files_without_rewriting_unchanged_files(self):
        override = self.root / "overlay" / "config.txt"
        override.write_text("overlay configuration\n")
        workspace = self.prepare()
        build = workspace / "src" / "pkg" / "BUILD.bazel"
        first_mtime = build.stat().st_mtime_ns
        self.prepare()
        self.assertEqual(build.stat().st_mtime_ns, first_mtime)
        overlay_build = self.root / "overlay" / "src" / "pkg" / "BUILD.bazel"
        overlay_build.write_text("# second\n")
        self.prepare()
        self.assertEqual(build.read_text(), "# second\n")
        overlay_build.unlink()
        override.unlink()
        self.prepare()
        self.assertFalse(build.exists())
        self.assertEqual((workspace / "config.txt").read_text(), "original configuration\n")

    def test_detects_generated_edits_before_applying_other_changes(self):
        workspace = self.prepare()
        build = workspace / "src" / "pkg" / "BUILD.bazel"
        build.write_text("edited in the wrong tree\n")
        (self.root / "overlay" / "new.txt").write_text("new overlay file\n")
        with self.assertRaisesRegex(ValueError, "Generated file was edited"):
            self.prepare()
        self.assertFalse((workspace / "new.txt").exists())
        self.assertEqual(build.read_text(), "edited in the wrong tree\n")

    def test_local_settings_are_separate_and_cannot_replace_published_files(self):
        local = self.root / ".local" / "workspace"
        local.mkdir(parents=True)
        (local / ".bazelrc").write_text("# local settings\n")
        workspace = self.prepare()
        self.assertEqual((workspace / ".bazelrc").read_text(), "# local settings\n")
        (local / "src" / "pkg").mkdir(parents=True)
        (local / "src" / "pkg" / "BUILD.bazel").write_text("# conflicting\n")
        with self.assertRaisesRegex(ValueError, "Local files conflict"):
            self.prepare()
        self.assertEqual((workspace / "src" / "pkg" / "BUILD.bazel").read_text(), "# first\n")

    def test_refuses_symlink_targets_outside_the_generated_workspace(self):
        workspace = self.prepare()
        outside = self.base / "outside"
        (outside / "pkg").mkdir(parents=True)
        victim = outside / "pkg" / "BUILD.bazel"
        victim.write_text("leave this alone\n")
        shutil.rmtree(workspace / "src")
        (workspace / "src").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.prepare()
        self.assertEqual(victim.read_text(), "leave this alone\n")

    def test_revision_change_requires_explicit_refresh(self):
        self.prepare()
        (self.source / "upstream.txt").write_text("new upstream version\n")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--no-gpg-sign", "-qm", "Next upstream fixture")
        self.config["revision"] = self.git("rev-parse", "HEAD")
        self.write_config()
        with self.assertRaisesRegex(ValueError, "revision changed"):
            self.prepare()
        workspace = self.prepare(refresh=True)
        self.assertEqual((workspace / "upstream.txt").read_text(), "new upstream version\n")


if __name__ == "__main__":
    unittest.main()
