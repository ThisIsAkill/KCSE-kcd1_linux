#pragma once

#include <windows.h>

namespace AsiLoader {

// Scans the directory the running module (hSelf) lives in for *.asi files
// and LoadLibrary()s each one -- the same convention Ultimate ASI Loader
// uses. Lets existing ASI-format mods (native code patches that aren't KCSE
// plugins, e.g. MinHook-based ones) drop in next to dinput8.dll and load
// automatically, without needing a separate ASI loader DLL that would
// otherwise fight KCSE for the same dinput8.dll proxy slot.
void Init(HMODULE hSelf);

}  // namespace AsiLoader
