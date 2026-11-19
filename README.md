# SLEEF Bazel overlay

Independent Bazel build support for upstream SLEEF 3.9.0. This repository tracks
build definitions, our test launcher, and development helpers. Upstream SLEEF
implementation sources are fetched separately and are never committed here.

## Layout

- `overlay/`: files to copy onto the root of upstream SLEEF, preserving paths.
- `upstream.json`: the upstream repository, release, and exact Git commit.
- `tools/`: preparation and test helpers.
- `docs/`: migration history and build-parity findings.
- `.work/`: ignored upstream cache, pristine snapshot, and combined build tree.
- `.local/workspace/`: ignored optional machine-specific files to copy into the
  combined tree, including `.bazelrc` and `toolchains/`.

## Prepare and test

Requires Python 3.12+, Git, Bazel 9.2.0 (or Bazelisk), and a C/C++ toolchain with
C++20 and OpenMP support. GCC needs its OpenMP runtime; Clang needs the matching
OpenMP development files and runtime. No compiler is installed or registered by
these scripts. Bazel resolves the compiler toolchain supplied by the consumer.

```sh
python3 tools/prepare.py
bash tools/test.sh
```

Preparation fetches the pinned upstream Git commit, verifies its identity, and
exports its tracked source tree with `git archive`. It then applies the overlay.
Subsequent runs synchronize changed overlay files without recreating the source
tree. Removed overlay files are removed from the build tree, or restored from
pristine upstream if they replaced an existing source file.

For offline use, point to an existing checkout containing the pinned commit:

```sh
export SLEEF_SOURCE_REPO=/path/to/your/sleef-checkout
python3 tools/prepare.py
bash tools/test.sh
```

The source checkout is read only: uncommitted changes and Bazel-port commits in
that checkout are not exported. Only the pinned upstream commit is used.

Edit **`overlay/`**, then run `prepare.py` or `test.sh` again. Read the upstream
sources under `.work/pristine/` or `.work/sleef/`. The helper detects edits to
managed files in the generated tree and stops rather than overwriting them.
`python3 tools/prepare.py --refresh` recreates the generated trees and discards
all edits inside them; use it after intentionally changing the upstream pin.

Additional Bazel test options and targets are passed through by `test.sh`:

```sh
bash tools/test.sh --test_output=errors
bash tools/test.sh --repo_env=CC=/usr/bin/clang
```

For other commands, prepare first and run Bazel inside the combined tree:

```sh
cd .work/sleef
USE_BAZEL_VERSION=9.2.0 bazel build -c opt //src/libm //src/dft
```

The preparation helper has its own offline regression checks:

```sh
python3 -m unittest discover -s tools -p test_prepare.py -v
```

## Local settings

Place optional `.bazelrc` and `toolchains/` under `.local/workspace/`, then rerun
preparation. They are copied into the combined tree so existing labels such as
`//toolchains:linux_aarch64` work. Local files cannot replace published overlay
files. The entire `.local/` and `.work/` directories are ignored by Git and must
not be included in published overlays. Untracked local files do not travel with
a clone of this repository.

The default DFT tests require execution on the target architecture. Cross-build
test binaries with `bazel build`, rather than `bazel test`; do not execute
AArch64 binaries on an x86 host without an execution environment or emulator.

## History and publication

The six original Bazel-port commits retain their messages, authors, committers,
and both timestamps. Their paths were moved under `overlay/`, so commit hashes
changed. See `docs/history.md` for the original-to-new mapping.

For BCR submission, use the official upstream source archive as the source and
copy these overlay files into the module version's `overlay/` directory. Generate
the source/overlay integrity hashes and registry metadata separately. This repo
is not itself a complete registry. Its local Git preparation workflow is for
development; BCR publication uses an archive source.

## License

The overlay is distributed under the Boost Software License 1.0, matching the
SLEEF version it targets. See `LICENSE` and `NOTICE.md`. This is independently
maintained build support, not an official SLEEF repository.
