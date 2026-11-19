load("@rules_cc//cc:defs.bzl", "cc_library")

def _implementation_library(
        name,
        visibility,
        mkrename_params,
        copts,
        additional_srcs,
        additional_defines):
    native.genrule(
        name = name + "_generated_rename",
        outs = ["include/rename%s.h" % name],
        cmd = "$(location //src/libm:mkrename) %s > $@" % mkrename_params,
        tools = ["//src/libm:mkrename"],
    )

    cc_library(
        name = name + "_nondeterministic",
        srcs = [
            "//src/libm:simd_sources",
            ":%s_generated_rename" % name,
        ] + additional_srcs,
        copts = [
            "-ffp-contract=off",
        ] + copts,
        includes = [
            ".",
            "include",
        ],
        linkstatic = True,
        local_defines = [
            "DORENAME",
            "ENABLE_%s" % name.upper(),
        ] + additional_defines,
        deps = [
            "//src/libm:rempitab",
            "//src/arch:headers",
            "//src/common",
            "//src/common:headers",
        ],
    )

    cc_library(
        name = name + "_deterministic",
        srcs = [
            "//src/libm:simd_sources",
            ":%s_generated_rename" % name,
        ] + additional_srcs,
        copts = [
            "-ffp-contract=off",
        ] + copts,
        includes = [
            ".",
            "include",
        ],
        linkstatic = True,
        local_defines = [
            "DORENAME",
            "ENABLE_%s" % name.upper(),
            "DETERMINISTIC=1",
        ] + additional_defines,
        deps = [
            "//src/libm:rempitab",
            "//src/arch:headers",
            "//src/common",
            "//src/common:headers",
        ],
    )

    cc_library(
        name = name,
        deps = [
            ":%s_deterministic" % name,
            ":%s_nondeterministic" % name,
        ],
    )

implementation_library = macro(
    attrs = {
        "mkrename_params": attr.string(mandatory = True, configurable = False),
        "copts": attr.string_list(mandatory = False, configurable = True, default = []),
        "additional_srcs": attr.label_list(mandatory = False, configurable = False, default = []),
        "additional_defines": attr.string_list(mandatory = False, configurable = False, default = []),
    },
    implementation = _implementation_library,
)
