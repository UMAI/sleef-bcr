#!/usr/bin/env python3
"""Materialize pinned upstream SLEEF and synchronize the overlay into it."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def directory(path):
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ValueError(f"Expected a real directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(layer):
    files = {}
    if layer.is_symlink():
        raise ValueError(f"Overlay directories cannot be symlinks: {layer}")
    if not layer.exists():
        return files
    for path in sorted(layer.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Overlay files cannot be symlinks: {path}")
        relative = path.relative_to(layer).as_posix()
        if ".git" in path.relative_to(layer).parts:
            raise ValueError(f"Git metadata must not be overlaid: {path}")
        if path.is_file():
            files[relative] = path
    return files


def target_path(workspace, relative):
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or ".." in parts or ".git" in parts:
        raise ValueError(f"Invalid overlay path: {relative}")
    target = workspace / relative
    for path in [target, *target.parents]:
        if path == workspace:
            break
        if path.is_symlink():
            raise ValueError(f"Refusing to overwrite through a symlink: {path}")
    if target.exists() and not target.is_file():
        raise ValueError(f"Expected a regular file: {target}")
    return target


def source_repository(work, config, source_repo):
    revision = config["revision"]
    if source_repo:
        repo = Path(source_repo).expanduser().resolve()
    else:
        repo = work / "upstream.git"
        if repo.is_symlink():
            raise ValueError(f"Source cache cannot be a symlink: {repo}")
        if not repo.exists():
            subprocess.run(["git", "init", "--bare", str(repo)], check=True,
                           stdout=subprocess.DEVNULL)
        check = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", revision + "^{commit}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if check.returncode:
            subprocess.run(["git", "-C", str(repo), "fetch", "--depth=1",
                            config["repository"], revision], check=True)
    actual = git(repo, "rev-parse", revision + "^{commit}")
    if actual != revision:
        raise ValueError(f"Unexpected upstream revision: {actual}")
    return repo


def materialize(work, pristine, workspace, config, source_repo):
    repo = source_repository(work, config, source_repo)
    with tempfile.TemporaryDirectory(prefix="extract-", dir=work) as temporary:
        temporary = Path(temporary)
        archive_path = temporary / "source.tar"
        with archive_path.open("wb") as archive:
            subprocess.run(["git", "-C", str(repo), "archive", "--format=tar",
                            config["revision"]], check=True, stdout=archive)
        extracted = temporary / "source"
        extracted.mkdir()
        with tarfile.open(archive_path) as archive:
            archive.extractall(extracted, filter="data")
        extracted.rename(pristine)
    shutil.copytree(pristine, workspace, symlinks=True)


def prepare(root, source_repo=None, refresh=False):
    config = json.loads((root / "upstream.json").read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", config["revision"]):
        raise ValueError("upstream.json must pin a full Git commit hash")
    work = root / ".work"
    workspace = work / "sleef"
    pristine = work / "pristine"
    state_path = work / "overlay-state.json"
    directory(work)
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    for path in (workspace, pristine, state_path):
        if path.is_symlink():
            raise ValueError(f"Generated paths cannot be symlinks: {path}")
    if refresh:
        # Only these two generated directories are discarded; never the source repo.
        for path in (workspace, pristine):
            if path.exists():
                shutil.rmtree(path)
        state_path.unlink(missing_ok=True)
        state = {}
    if state and state["revision"] != config["revision"]:
        raise ValueError("Upstream revision changed; rerun with --refresh")
    if not state:
        if workspace.exists() or pristine.exists():
            raise ValueError("Incomplete generated tree; rerun with --refresh")
        materialize(work, pristine, workspace, config, source_repo)
    elif not workspace.is_dir() or not pristine.is_dir():
        raise ValueError("Missing generated tree; rerun with --refresh")

    files = collect(root / "overlay")
    local = collect(root / ".local" / "workspace")
    overlap = files.keys() & local.keys()
    if overlap:
        raise ValueError("Local files conflict with the overlay: " + ", ".join(sorted(overlap)))
    files.update(local)
    hashes = {name: digest(path) for name, path in files.items()}
    previous = state.get("files", {})
    # Check all managed files before changing any of them. Edits belong in overlay/.
    for name in previous.keys() | files.keys():
        target = target_path(workspace, name)
        if name in previous and target.exists():
            current = digest(target)
            if current != previous[name] and current != hashes.get(name):
                raise ValueError(f"Generated file was edited: {target}. "
                                 "Move the edit to overlay/ (or use --refresh to discard it).")
    for name in previous.keys() - files.keys():
        target = target_path(workspace, name)
        original = pristine / name
        if original.is_file() and not original.is_symlink():
            shutil.copy2(original, target)
        else:
            target.unlink(missing_ok=True)
    for name, source in files.items():
        target = target_path(workspace, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or digest(target) != hashes[name]:
            shutil.copy2(source, target)
        else:
            shutil.copymode(source, target)
    temporary_state = work / "overlay-state.tmp"
    temporary_state.write_text(json.dumps({
        "revision": config["revision"], "files": hashes,
    }, indent=2, sort_keys=True) + "\n")
    temporary_state.replace(state_path)
    return workspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", default=os.environ.get("SLEEF_SOURCE_REPO"),
                        help="existing SLEEF Git checkout for offline preparation")
    parser.add_argument("--refresh", action="store_true",
                        help="discard and recreate the generated source trees")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or newer is required for safe archive extraction")
    try:
        workspace = prepare(ROOT, args.source_repo, args.refresh)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError,
            tarfile.TarError) as error:
        parser.exit(1, f"prepare: {error}\n")
    print(f"Prepared {workspace}")


if __name__ == "__main__":
    main()
