"""DFT options selected from the actual target C/C++ toolchain."""

load("@rules_cc//cc:find_cc_toolchain.bzl", "CC_TOOLCHAIN_ATTRS", "find_cc_toolchain", "use_cc_toolchain")

DFT_COPTS = [
    "-std=c++20",
    "-fno-strict-aliasing",
    "-fno-math-errno",
    "-fno-trapping-math",
    "-fopenmp",
    "$(SLEEF_DFT_COMPILER_FLAGS)",
]

def _compiler_options_impl(ctx):
    compiler = find_cc_toolchain(ctx).compiler
    is_clang = compiler in ["clang", "llvm"]

    # Follow CMake: Clang leaves scalar kernels unoptimized, and GCC SVE
    # kernels retain the workaround for GCC 10 value-range propagation.
    return [platform_common.TemplateVariableInfo({
        "SLEEF_DFT_COMPILER_FLAGS": "-ffast-math" if is_clang else "",
        "SLEEF_DFT_SCALAR_FLAGS": "-O0" if is_clang else "",
        "SLEEF_DFT_SVE_FLAGS": "-fno-tree-vrp" if compiler == "gcc" else "",
    })]

compiler_options = rule(
    implementation = _compiler_options_impl,
    attrs = CC_TOOLCHAIN_ATTRS,
    fragments = ["cpp"],
    toolchains = use_cc_toolchain(),
)
