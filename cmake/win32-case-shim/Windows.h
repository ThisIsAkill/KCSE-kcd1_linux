#pragma once
// MinGW's sysroot only ships windows.h (lowercase). libKCD1's REL sources
// #include <Windows.h> (MSVC is case-insensitive), which fails to resolve on
// Linux's case-sensitive filesystem. This directory is added ahead of the
// mingw include path so that include resolves here instead.
#include <windows.h>
