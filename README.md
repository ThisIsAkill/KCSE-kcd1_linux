# KCSE — Kingdom Come Script Extender

[![C++17](https://img.shields.io/static/v1?label=standard&message=C%2B%2B17&color=blue&logo=c%2B%2B&logoColor=white&style=flat)](https://en.cppreference.com/w/cpp/compiler_support)
[![Platform](https://img.shields.io/static/v1?label=platform&message=windows%20%7C%20linux%20(cross--compile)&color=dimgray&style=flat)](#)
[![License](https://img.shields.io/static/v1?label=license&message=GPLv3&color=blue&style=flat)](LICENSE)

KCSE is an SKSE-style native plugin framework for **Kingdom Come: Deliverance 1**. It loads as a `dinput8.dll` proxy — no exe patching, ASI loaders, or repacking required — and gives mod plugins a stable API for hooking game events, running code on the main thread, and resolving function/data addresses across game builds via an address library.

This fork adds first-class support for building and testing KCSE **on Linux**, cross-compiling the DLL with MinGW-w64 and validating it under Wine/Proton, in addition to the native Windows/MSVC toolchain.

## How it works

`dinput8.dll` sits next to the game's real `dinput8.dll` calls (Kingdom Come: Deliverance loads `dinput8.dll` at startup, which most Windows systems resolve to the system DLL). KCSE's proxy forwards every export to the real system library so the game behaves exactly as before, then spins up a background thread that:

1. Waits for the core CryEngine subsystems to be ready.
2. Installs a code-cave trampoline for hooking engine functions.
3. Installs the task queue and event dispatcher hooks.
4. Loads every plugin DLL and hands each one a `KCSE::IKCSEInterface*`.
5. Dispatches lifecycle messages (`DataLoaded`, `NewGame`, `LoadGame`, `SaveGame`, `AllPluginsLoaded`) as the game reaches each stage.

Because CryEngine's internal addresses shift between game builds, KCSE never hardcodes offsets in plugin code. Instead it resolves them at runtime through **libKCD1**'s address-library database, keyed off the running executable's build.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | KCSE core: DLL proxy, plugin manager, event dispatcher, task interface, trampoline glue |
| `src/dll_proxy/` | The `dinput8.dll` export-forwarding shim |
| `extern/libKCD1/` | [libKCD1](https://github.com/JerryYOJ/libKCD1) reverse-engineering/address-library submodule |
| `addresslib/` | Human-editable offset mappings (`mappings/<dist>_<build>.txt`) and `gen_addresslib.py`, which compiles them into the binary format `REL::IDDatabase` loads at runtime |
| `cmake/` | CMake helpers, including the MinGW-w64 cross-compilation toolchain file |
| `test/` | `loader.cpp`, a minimal Windows executable used to smoke-test the DLL under Wine without the real game |
| `build.sh` / `dev-cycle.sh` | Linux build and build-test-deploy scripts (see below) |

## Build Dependencies

- [libKCD1](https://github.com/JerryYOJ/libKCD1) — bundled as a git submodule at `extern/libKCD1`
- [spdlog](https://github.com/gabime/spdlog) — resolved via vcpkg/system package if available, otherwise fetched automatically by CMake
- [CMake 3.15+](https://cmake.org/)

**Windows:**
- [Visual Studio 2022+](https://visualstudio.microsoft.com/) with the "Desktop development with C++" workload
- [vcpkg](https://github.com/microsoft/vcpkg)

**Linux (cross-compiling a Windows DLL):**
- `mingw-w64` (`sudo apt install mingw-w64`)
- `wine` (optional, only needed for the smoke test)

## End User Dependencies

- [Kingdom Come: Deliverance 1](https://store.steampowered.com/app/379430/Kingdom_Come_Deliverance/) (tested against 1.9.7.0)

## Building on Windows

```sh
git submodule update --init
cmake -B build -DCMAKE_TOOLCHAIN_FILE=<path-to-vcpkg>/scripts/buildsystems/vcpkg.cmake
cmake --build build --config Release
```

The DLL is produced as `build/Release/dinput8.dll`.

## Building on Linux

`build.sh` cross-compiles `dinput8.dll` with MinGW-w64 and initializes the `libKCD1` submodule automatically:

```sh
./build.sh
```

The DLL is produced at `build-mingw/dinput8.dll`. Deploy it into your Steam/Proton prefix:

```sh
cp build-mingw/dinput8.dll ~/.steam/steam/steamapps/common/KingdomComeDeliverance/Bin/Win64/
```

To sanity-check that the DLL loads and initializes correctly without launching the full game, run the Wine smoke test:

```sh
cmake --build build-mingw --target smoke_test
```

`dev-cycle.sh` wraps build, deploy, and verification into a single loop for iterative development:

```sh
./dev-cycle.sh          # build + Wine smoke test (fast, no game)
./dev-cycle.sh --game   # build + deploy + full game launch via Steam, watches KCSE.log
```

`GAME_DIR` overrides the default Steam install path (`~/.steam/steam/steamapps/common/KingdomComeDeliverance`).

## Address Library

KCSE resolves engine addresses by ID rather than hardcoded offset, so the same plugin binary keeps working across game patches as long as a mapping exists for that build. Mappings live in `addresslib/mappings/<dist>_<build_key>.txt` (one `<id> <hex offset>` pair per line) and are compiled into the binary format the runtime loads with:

```sh
python3 addresslib/gen_addresslib.py <game>/KCSE/addresslib addresslib/mappings/steam_<build_key>.txt
```

`dev-cycle.sh --game` runs this step automatically before launching the game.

## Installation (end users)

1. Copy `dinput8.dll` to `<game>/Bin/Win64/`.
2. Generate the address library for your installed game build into `<game>/KCSE/addresslib/` (see above).
3. Drop plugin DLLs into `<game>/KCSE/Plugins/` (or `mods/<modname>/KCSE/Plugins/` for mod-manager-friendly packaging).

## Plugin Development

```cpp
#include "KCSE/KCSEAPI.h"

KCSE_PLUGIN_INFO("MyPlugin", "Author", 1);

KCSE_PLUGIN_LOAD(kcse)
{
    kcse->GetMessagingInterface()->RegisterListener([](KCSE::Message* msg) {
        if (msg->type == KCSE::IMessagingInterface::kMessage_DataLoaded) {
            // Game data loaded
        }
    });

    return true;
}
```

- KCSE auto-calls `KCSE::Init()` when using the `KCSE_PLUGIN_LOAD` macro.
- Available lifecycle messages: `DataLoaded`, `LoadGame`, `SaveGame`, `NewGame`, `AllPluginsLoaded`.
- Per-frame tasks via `KCSE::GetTaskInterface()->AddTask(fn)`.
- Trampoline hooking via `KCSE::GetTrampoline()`.

## Contributing

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before opening issues or pull requests.

## License

[GPLv3](LICENSE)
