#include <windows.h>
#include <stdio.h>

int main()
{
    HMODULE h = LoadLibraryA("dinput8.dll");
    if (!h) {
        fprintf(stderr, "LoadLibrary failed: %lu\n", GetLastError());
        return 1;
    }
    // DllMain spawns MainThread which logs "Initializing" then blocks
    // waiting for CCryAction.  Give it a moment to write the log.
    Sleep(2000);
    FreeLibrary(h);
    return 0;
}
