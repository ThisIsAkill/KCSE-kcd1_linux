#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build-mingw"
TOOLCHAIN="${SCRIPT_DIR}/cmake/toolchain-mingw64.cmake"

# Ensure submodule is populated
if [ ! -f "${SCRIPT_DIR}/extern/libKCD1/include/KCSE/KCSEAPI.h" ]; then
    echo "Initializing submodules..."
    git -C "${SCRIPT_DIR}" submodule update --init
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
