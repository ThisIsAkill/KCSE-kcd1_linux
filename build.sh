#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build-mingw"
TOOLCHAIN="${SCRIPT_DIR}/cmake/toolchain-mingw64.cmake"
RE_ROOT="${SCRIPT_DIR}/extern/libKCD1"
PATCH="${SCRIPT_DIR}/patches/libKCD1-mingw-crythread.patch"

# Ensure submodule is populated
if [ ! -f "${RE_ROOT}/include/KCSE/KCSEAPI.h" ]; then
    echo "Initializing submodules..."
    git -C "${SCRIPT_DIR}" submodule update --init
fi

# CrySimpleThread<T>'s destructor references gEnv before ISystem.h (which
# declares it) is included anywhere in platform.h's chain. MSVC defers this
# lookup to instantiation (and nothing ever instantiates CrySimpleThread<T>);
# GCC's two-phase lookup requires it resolved at template definition, so the
# PCH fails to build under MinGW without this patch.
if ! git -C "${RE_ROOT}" apply --reverse --check "${PATCH}" 2>/dev/null; then
    echo "Patching libKCD1 for MinGW gEnv visibility..."
    git -C "${RE_ROOT}" apply "${PATCH}"
fi

# Configure (only if not already configured)
if [ ! -f "${BUILD_DIR}/build.ninja" ] && [ ! -f "${BUILD_DIR}/Makefile" ]; then
    echo "Configuring..."
    cmake -B "${BUILD_DIR}" \
        -DCMAKE_TOOLCHAIN_FILE="${TOOLCHAIN}"
fi

# Build
echo "Building..."
cmake --build "${BUILD_DIR}" --parallel

echo ""
echo "Output: ${BUILD_DIR}/dinput8.dll"
echo ""
echo "Deploy:  cp ${BUILD_DIR}/dinput8.dll ~/.steam/steam/steamapps/common/KingdomComeDeliverance/Bin/Win64/"
echo "Verify:  cmake --build ${BUILD_DIR} --target smoke_test"
