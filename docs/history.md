# History extraction

The overlay history was extracted from the local SLEEF Bazel-port branch after
upstream tag `3.9.0` (commit `906ca7512ee483296780a81a21b9ca715d40dfe1`).

All six commits remain distinct and in their original order. Author and committer
names, email addresses, timestamps, timezone offsets, and complete messages were
preserved byte for byte. Every retained file's contents and executable mode were
also verified against its source commit. Paths now start with `overlay/`, so
trees, parents, and commit IDs changed.

| Original commit | Overlay commit | Subject |
| --- | --- | --- |
| `b4f12bb8916c` | `3ad8a48d92c3` | Add Bazel build and tests for scalar libm variants |
| `d602c74daf96` | `24eca167527e` | Add SSE dispatcher and SSE2/SSE4/AVX2128 implementations behind it |
| `15d961a5cbb9` | `c4776e494892` | Add AVX dispatcher and implementation libraries |
| `f9f2c2c33651` | `3a15860d2170` | Add AVX512 implementations to x86_64 platform |
| `d4314e51c23d` | `c17ff13fdd9e` | Add aarch64 architecture support |
| `8f9bca24113a` | `9ea9fae6cdea` | Added DFT library and the appropriate implementations |

Only the selected BUILD.bazel, MODULE.bazel, .bzl files and the new
`planner_test_main.cc` launcher were retained. No original SLEEF implementation
sources or upstream commit ancestry were imported. Local `.bazelrc`, toolchain
definitions, generated lockfiles, and the old workspace's `.gitignore` were
excluded from every historical commit.

The initial overlay commit is a root commit. Extraction used Git's object and
tree commands in a separate repository; the original checkout and its working
changes were left untouched. The initial six commits contain only `overlay/`.
Repository helpers, attribution, and documentation were added in a seventh commit.

Uncommitted local compiler and toolchain settings may be present under the
ignored `.local/workspace/` directory in this prepared working copy. They are
not part of any commit and are not part of the published overlay.
