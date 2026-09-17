#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build-mingw"
TOOLCHAIN="${SCRIPT_DIR}/cmake/toolchain-mingw64.cmake"
RE_ROOT="${SCRIPT_DIR}/extern/libKCD1"

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
#
# MSVC doesn't vtable-order same-name virtual overloads by declaration order
# the way Itanium/GCC does; IMessagingInterface::RegisterListener's two
# overloads land in the opposite vtable slots in every existing prebuilt
# (MSVC-built) plugin, which silently corrupted their RegisterListener(EventCallback)
# calls into landing on the wrong slot with garbage arguments. Reordering the
# declarations to match MSVC's actual layout restores drop-in binary
# compatibility with prebuilt plugin DLLs.
#
# libstdc++'s std::map/std::unordered_map differ in size from MSVC STL's;
# several guimodule/playermodule structs (C_UIMap, C_UIMapCloudAtlas,
# C_FastTravel) fail their layout static_asserts when built under MinGW
# without this.
for PATCH in \
    "${SCRIPT_DIR}/patches/libKCD1-mingw-crythread.patch" \
    "${SCRIPT_DIR}/patches/libKCD1-msvc-vtable-order.patch" \
    "${SCRIPT_DIR}/patches/libKCD1-mingw-guimodule-struct-layout.patch"
do
    if ! git -C "${RE_ROOT}" apply --reverse --check "${PATCH}" 2>/dev/null; then
        echo "Patching libKCD1: $(basename "${PATCH}")..."
        git -C "${RE_ROOT}" apply "${PATCH}"
    fi
done

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
