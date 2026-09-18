#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build-mingw"
TOOLCHAIN="${SCRIPT_DIR}/cmake/toolchain-mingw64.cmake"

# Ensure submodule is populated and compatibility patches are applied
# (shared with dev-cycle.sh -- see cmake/apply-libkcd1-patches.sh).
"${SCRIPT_DIR}/cmake/apply-libkcd1-patches.sh"

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
