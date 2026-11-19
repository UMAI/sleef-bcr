"""Generate and compile one float or double DFT kernel family."""

load("@rules_cc//cc:defs.bzl", "cc_library")
load(":compiler_options.bzl", "DFT_COPTS")

def _dft_kernel_impl(name, visibility, precision, enable, config, copts, local_defines, target_compatible_with):
    base_type, base_type_id = {
        "dp": ("double", 1),
        "sp": ("float", 2),
    }[precision]

    # mkunroll writes named files in its current directory. Resolve the inputs
    # before entering the output directory.
    native.genrule(
        name = name + "_generate_unroll",
        srcs = [Label("//src/dft:unroll_template")],
        outs = ["unroll_%d_%s.cpp" % (variant, name) for variant in [0, 2]],
        cmd = """
tool="$$PWD/$(execpath //src/dft:mkunroll)"
template="$$PWD/$(location //src/dft:unroll_template)"
cd "$(@D)"
"$$tool" "$$template" %s %s - %s
""" % (base_type, precision.upper(), name),
        tools = [Label("//src/dft:mkunroll")],
        visibility = ["//src/dft:__pkg__"],
    )

    compiler_copts = []
    if enable == "PUREC":
        compiler_copts.append("$(SLEEF_DFT_SCALAR_FLAGS)")
    if enable == "SVE":
        compiler_copts.append("$(SLEEF_DFT_SVE_FLAGS)")

    cc_library(
        name = name,
        srcs = [
            Label("//src/dft:kernel_headers"),
            ":" + name + "_generate_unroll",
        ],
        copts = DFT_COPTS + compiler_copts + copts,
        includes = ["."],
        linkopts = ["-fopenmp"],
        linkstatic = True,
        local_defines = [
            "BASETYPEID=%d" % base_type_id,
            "CONFIG=%d" % config,
            "ENABLE_" + enable,
        ] + local_defines,
        target_compatible_with = target_compatible_with,
        toolchains = [Label("//src/dft:compiler_options")],
        visibility = visibility,
        deps = [
            Label("//include:sleefdft_headers"),
            Label("//src/arch:headers"),
            Label("//src/common:headers"),
            Label("//src/libm"),
        ],
    )

dft_kernel = macro(
    implementation = _dft_kernel_impl,
    attrs = {
        "precision": attr.string(mandatory = True, configurable = False, values = ["dp", "sp"]),
        "enable": attr.string(mandatory = True, configurable = False),
        "config": attr.int(mandatory = True, configurable = False),
        "copts": attr.string_list(default = []),
        "local_defines": attr.string_list(default = ["MAXBUTWIDTHDP=4", "MAXBUTWIDTHSP=4"]),
        "target_compatible_with": attr.label_list(default = []),
    },
)
