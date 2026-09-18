#!/usr/bin/env bash
# Ensures extern/libKCD1 is populated and its compatibility patches are
# applied. Shared by build.sh and dev-cycle.sh so both build paths stay in
# sync -- a patch step that only build.sh ran was silently bypassed for a
# whole session by calling `cmake --build` directly instead, which left
# IMessagingInterface::RegisterListener's vtable-order fix unapplied and
# every plugin's registration silently failing with no error.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RE_ROOT="${SCRIPT_DIR}/extern/libKCD1"

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
