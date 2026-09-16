cmake_minimum_required(VERSION 3.15)
project(KCSE LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── libKCD1 ──────────────────────────────────────────────────────────────────
# Clone from https://github.com/JerryYOJ/libKCD1 and pass -DRE_ROOT=/path/to/it

if(NOT DEFINED RE_ROOT)
    set(RE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/extern/libKCD1")
endif()
if(NOT EXISTS "${RE_ROOT}/include")
    message(FATAL_ERROR
        "libKCD1 headers not found at ${RE_ROOT}/include.\n"
        "Run:  git submodule update --init\n"
        "or pass -DRE_ROOT=/path/to/libKCD1 to point to a manual clone.")
endif()

add_library(kcd_re INTERFACE)
target_include_directories(kcd_re INTERFACE
    ${RE_ROOT}/include
    ${RE_ROOT}/include/CryEngine/CryCommon)

# ── spdlog ───────────────────────────────────────────────────────────────────
# Resolved via vcpkg if available, otherwise fetched automatically.

if(NOT CMAKE_CROSSCOMPILING)
    find_package(spdlog QUIET)
endif()
if(NOT spdlog_FOUND)
    include(FetchContent)
    FetchContent_Declare(
        spdlog
        GIT_REPOSITORY https://github.com/gabime/spdlog.git
        GIT_TAG        v1.14.1)
    FetchContent_MakeAvailable(spdlog)
endif()

# ── KCSE shared library ───────────────────────────────────────────────────────

file(GLOB_RECURSE KCSE_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

# libKCD1 ships REL::Module / REL::IDDatabase (address-library resolution) as
# plain .cpp sources rather than headers; KCSE needs them at runtime to turn
# REL::ID(...) into real addresses (e.g. Offsets::GetCCryAction()). Everything
# else in libKCD1/src is reversed-engineered game-module glue that KCSE's core
# loader doesn't touch, so only these two are pulled in.
list(APPEND KCSE_SOURCES
    "${RE_ROOT}/src/REL/Module.cpp"
    "${RE_ROOT}/src/REL/IDDatabase.cpp")

add_library(KCSE SHARED ${KCSE_SOURCES})

target_compile_definitions(KCSE PRIVATE
    _ITERATOR_DEBUG_LEVEL=0 WIN32_LEAN_AND_MEAN NOMINMAX)

if(MSVC)
    target_compile_options(KCSE PRIVATE /utf-8 /W4 /wd4819 /wd4100)
else()
    target_compile_options(KCSE PRIVATE
        -Wall -Wno-unused-parameter
        -fpermissive              # CryEngine headers have MSVC-only constructs
        -Wno-deprecated-declarations)
    # -static also pulls in libwinpthread statically; without it dinput8.dll
    # depends on libwinpthread-1.dll, which isn't shipped next to the game.
    target_link_options(KCSE PRIVATE -static-libgcc -static-libstdc++ -static)
endif()

target_include_directories(KCSE PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

if(NOT MSVC)
    # libKCD1's REL sources #include <Windows.h> (MSVC is case-insensitive);
    # MinGW's sysroot only ships lowercase windows.h. Shim the capitalized
    # name on Linux's case-sensitive filesystem.
    target_include_directories(KCSE PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/cmake/win32-case-shim)
endif()

target_precompile_headers(KCSE PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/PCH.h)

if(MSVC)
    target_link_libraries(KCSE PRIVATE kcd_re spdlog::spdlog version.lib)
else()
    target_link_libraries(KCSE PRIVATE kcd_re spdlog::spdlog version)
endif()


# MinGW's default shared-library prefix is "lib" (libdinput8.dll); Proton
# needs the literal filename dinput8.dll to intercept the game's dinput8 load.
set_target_properties(KCSE PROPERTIES OUTPUT_NAME "dinput8" PREFIX "")

# ---- Wine smoke-test (no game needed) ----
# Builds a tiny loader.exe; `cmake --build build-mingw --target smoke_test`
# runs it under wine, waits 3 s for KCSE.log to appear, then reports.
if(CMAKE_CROSSCOMPILING AND NOT MSVC)
    add_executable(kcse_loader test/loader.cpp)
    target_link_options(kcse_loader PRIVATE -static-libgcc -static-libstdc++)
    set_target_properties(kcse_loader PROPERTIES OUTPUT_NAME "loader")

    add_custom_target(smoke_test
        DEPENDS KCSE kcse_loader
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMAND ${CMAKE_COMMAND} -E rm -f KCSE/KCSE.log
        COMMAND ${CMAKE_COMMAND} -E make_directory KCSE
        COMMAND bash -c "timeout 5 wine loader.exe || true"
        COMMAND bash -c
            "if [ -f KCSE/KCSE.log ] && grep -q 'Initializing' KCSE/KCSE.log; then \
               echo '[PASS] KCSE loaded — log:'; cat KCSE/KCSE.log; \
             else \
               echo '[FAIL] KCSE.log missing or empty'; \
               [ -f KCSE/KCSE.log ] && cat KCSE/KCSE.log; exit 1; \
             fi"
        COMMENT "Running Wine smoke test..."
        VERBATIM
    )
endif()
