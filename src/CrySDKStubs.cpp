#include <windows.h>

// CryEngine expects these to be provided by the SDK/CRT it was linked against
// (see CryMemoryAllocator.h). They're thin wrappers over the equivalent Win32
// primitives, ported from libKCD1's own .buildenv/CrySDKStubs.cpp.
void CryCreateCriticalSectionInplace(void* p) { InitializeCriticalSection(static_cast<CRITICAL_SECTION*>(p)); }
void CryDeleteCriticalSectionInplace(void* p) { DeleteCriticalSection(static_cast<CRITICAL_SECTION*>(p)); }
