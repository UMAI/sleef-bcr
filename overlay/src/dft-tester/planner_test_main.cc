#include <cstdio>
#include <cstdlib>

#ifdef _WIN32
#include <direct.h>
#else
#include <unistd.h>
#endif

int sleef_dftplanner_main(int argc, char **argv);

int main(int argc, char **argv) {
  const char *test_tmpdir = std::getenv("TEST_TMPDIR");
  if (test_tmpdir == nullptr) {
    std::fputs("TEST_TMPDIR is required for the planner test\n", stderr);
    return 1;
  }

#ifdef _WIN32
  const int result = _chdir(test_tmpdir);
#else
  const int result = chdir(test_tmpdir);
#endif
  if (result != 0) {
    std::perror("Cannot enter TEST_TMPDIR");
    return 1;
  }

  return sleef_dftplanner_main(argc, argv);
}
