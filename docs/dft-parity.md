**SLEEF 3.9.0 DFT: CMake/Bazel parity verification — 2026-11-16**

The generated DFT code, kernel coverage, and public DFT API match CMake for
x86-64 and AArch64. The compiler options, C++20 setting, shared-library runtime
names, and local cross-toolchain optimization modes have now been aligned as
described below. This is correctness and interface parity, not a claim of
bit-identical binaries or equal performance.

The comparison used GCC/G++ 13.3.0, Clang/Clang++ 18.1.3, CMake 3.28.3,
and Bazel 9.2.0 with rules_cc 0.2.22 and platforms 1.1.0. The AArch64 reference
used aarch64-linux-gnu GCC/G++ 13.3.0. Native comparisons requested -O2 -DNDEBUG
on both build systems; CMake intentionally overrides scalar DFT kernels to -O0
under Clang. The AArch64 comparison explicitly supplied -O2 -DNDEBUG to Bazel
because our local cross-toolchain does not implement compilation-mode flags.

CMake built shared libraries with DFT enabled, streaming disabled, and the
normal architecture/compiler probes. QUAD, the separate GNU ABI library,
TLFloat, and optional FFTW/MPFR/OpenSSL test dependencies were disabled. This
leaves CMake's normal weak-alias probing enabled in the main math library.
The actual reference command used Release with CMAKE_C_FLAGS_RELEASE and
CMAKE_CXX_FLAGS_RELEASE both set to '-O2 -DNDEBUG' instead of Release's usual -O3.
Cached module sources and a local registry were used for Bazel's offline build;
the project's MODULE.bazel and build definitions were not modified.

| Check | x86-64 GCC | x86-64 Clang | AArch64 GCC |
| --- | --- | --- | --- |
| Generated dispatch headers and unrolled sources | 19/19 byte-identical | 19/19 byte-identical | 27/27 byte-identical |
| Exported kernel and backend metadata functions | 400/400 identical | 400/400 identical | 888/888 identical |
| Public SleefDFT_* functions | 13/13 identical | 13/13 identical | 13/13 identical |
| Bazel static/shared correctness suite | 56/56 passed | 56/56 passed | Not executed |
| CMake's registered DFT/planner CTests | 14/14 passed | 14/14 passed | Not executed |
| Unchanged Bazel shared-test executables using CMake libraries | 28/28 passed | 28/28 passed | Not executed |

The generated-file comparison covered dispatchparam.h, dispatchdp.hpp,
dispatchsp.hpp, and every enabled unroll_0/unroll_2 source. Files were compared
byte for byte. Kernel symbol comparisons used demangled dynamic symbols,
including butterflies, real-transform helpers, and getInt/getPtr functions.
The public header is the same upstream include/sleefdft.h in both builds.

The x86-64 lists contain pure C, SSE4.1 (upstream names sse2dp/sse2sp), AVX2,
and AVX-512F kernels. AArch64 contains pure C, Advanced SIMD, and SVE kernels
using 256-, 512-, 1024-, and 2048-bit partial vectors. Butterfly limits match
CMake: log2 width 4 on x86-64 and 6 on AArch64; min/max shift are both 1.

For the library substitution checks, the same 28 shared executables and
arguments were reused, with LD_LIBRARY_PATH pointing to CMake's lib directory.
ldd -r confirmed that both libsleefdft and libsleef resolved to those CMake
libraries without unresolved relocations. The drivers contain no embedded
SleefDFT_* implementations. This covers the reference cases, 1D/2D round trips,
serial variants, and measured/estimated planner tests with saved-plan reloads.
Each planner process had its own TEST_TMPDIR. These are correctness checks
within upstream tolerances, not a bitwise-output or performance benchmark.
Native execution selected AVX2. AVX-512 and AArch64 kernels were built and
inspected, but were not executed on this x86-64 host.

The six build differences identified in the initial comparison were addressed:

1. **Floating-point options:** DFT now uses -fno-math-errno and
   -fno-trapping-math, plus -ffast-math with Clang. These options apply to the
   engine and kernels; libm retains its separate, strict floating-point options.
2. **Clang scalar kernels:** purecdp/purecsp now append -O0 with Clang, matching
   CMake. GCC scalar kernels retain the selected compilation mode's optimization.
3. **GCC SVE workaround:** SVE kernels now append -fno-tree-vrp with GCC,
   matching upstream's GCC 10 value-range propagation workaround. Compiler-specific
   options are derived from the selected C/C++ toolchain at analysis time, rather
   than requiring consumers to set a separate compiler flag.
4. **C++ standard:** DFT now explicitly requests C++20. The local .bazelrc also
   selects C++20 for native target/host C++ actions, and the AArch64 toolchain
   enables it for C++ compilation. GCC/G++ 13.3.0, Clang 18.1.3, their development
   libraries, and the AArch64 G++ 13 cross-compiler were already installed.
   A probe using concepts and std::span compiled with all three; the native
   executables ran successfully. No additional package installation was needed.
   Bazel requests ISO C++20 while CMake uses the GNU C++20 dialect.
5. **Shared-library versions:** On Linux, libsleef and libsleefdft now emit real
   .so.3 files with matching shared-object names (SONAMEs). DFT records a
   dependency on libsleef.so.3. The sleef_shared_files/dft_shared_files targets
   additionally create unversioned .so and full-version .so.3.9.0 symlinks to
   those runtime files. CMake instead uses the full-version file as the physical
   library; both layouts provide the same three names and runtime SONAME.
   Bazel's normal shared targets produce the runtime files; use the *_shared_files
   targets when collecting the distribution aliases. Build-tree RUNPATH values,
   non-public C++ symbols, and some direct system-library dependencies can still
   differ. Both builds use libgomp with GCC and libomp with Clang.
6. **Local cross-toolchain modes:** The handwritten AArch64 toolchain now maps
   opt to -O2 -DNDEBUG, dbg to -O0 -g, and fastbuild to -O0. It no longer requires
   manual --copt overrides. This toolchain is local test infrastructure, outside
   the BCR overlay.

After these changes, the 56-test native Bazel suite passed again with both GCC
and Clang. All 14 CMake-built reference/planner clients also passed against the
new Bazel shared libraries for each compiler, with LD_LIBRARY_PATH pointing to
Bazel's output directories. Actual compile actions confirmed Clang's fast-math
and final scalar -O0 flags; ELF dynamic sections confirmed both versioned SONAMEs
and DFT's versioned math dependency. AArch64 opt compilation and linking also
passed for both shared libraries, their distribution aliases, and all 56 test
binaries, without manual optimization overrides. Compile-action inspection
confirmed GCC's SVE workaround and the opt/dbg/fastbuild mode flags. ELF headers
confirmed AArch64 output and the versioned runtime dependency. No AArch64 tests
were executed on this host.

The math dependency retains previously deferred differences. On x86-64,
CMake exports Sleef_sincospiq_u05 and Sleef_sincospiq_u35 plus 937 vector ABI
aliases that Bazel does not. On AArch64, the Sleef_* function sets match, but
151 vector ABI aliases remain absent from Bazel. These are libm deferrals;
there are no missing SleefDFT_* functions in this comparison.

Useful project commands are:

~~~sh
bazel test --config=gcc -c opt //src/dft-tester:all
bazel test --config=clang -c opt //src/dft-tester:all
bazel build --config=gcc -c opt \
  --platforms=//toolchains:linux_aarch64 \
  --extra_toolchains=//toolchains:aarch64_linux_toolchain \
  //src/dft:dft_shared_files //src/libm:sleef_shared_files
~~~

Detailed logs, compile commands, source hashes, symbol comparisons, and
individual library-substitution results from this run are in
/tmp/sleef-dft-parity-20261116.S74vto. The subsequent alignment checks are in
/tmp/sleef-build-alignment.1zj28X. Temporary artifacts may be cleared between
sessions; this report preserves the findings.
