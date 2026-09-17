#include "AsiLoader.h"
#include <filesystem>
#include <spdlog/spdlog.h>

namespace fs = std::filesystem;

namespace AsiLoader {

void Init(HMODULE hSelf)
{
    char selfPath[MAX_PATH];
    if (!GetModuleFileNameA(hSelf, selfPath, MAX_PATH)) {
        spdlog::warn("AsiLoader: could not resolve own module path, skipping .asi scan");
        return;
    }

    auto dir = fs::path(selfPath).parent_path();
    spdlog::info("AsiLoader: scanning {}", dir.string());

    if (!fs::exists(dir)) {
        spdlog::info("AsiLoader: directory does not exist, skipping");
        return;
    }

    int found = 0;
    for (auto& entry : fs::directory_iterator(dir)) {
        if (!entry.is_regular_file())
            continue;
        if (_stricmp(entry.path().extension().string().c_str(), ".asi") != 0)
            continue;

        auto path = entry.path().string();
        auto filename = entry.path().filename().string();
        ++found;

        // A .asi is just a renamed DLL that does its own init in DllMain (its
        // own hooking library, its own threads if it wants them) -- unlike
        // KCSE plugins, there's no KCSEPlugin_Load export to call and no
        // version/compatibility data to check. Loading it is enough.
        HMODULE hAsi = LoadLibraryA(path.c_str());
        if (!hAsi) {
            spdlog::warn("AsiLoader: failed to load {}: error {}", filename, GetLastError());
            continue;
        }

        spdlog::info("AsiLoader: loaded {}", filename);
    }

    if (!found)
        spdlog::info("AsiLoader: no .asi files found");
}

}  // namespace AsiLoader
