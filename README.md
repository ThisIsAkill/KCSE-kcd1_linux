# KCSE — Kingdom Come Script Extender (Linux)

[![C++17](https://img.shields.io/static/v1?label=standard&message=C%2B%2B17&color=blue&logo=c%2B%2B&logoColor=white&style=flat)](https://en.cppreference.com/w/cpp/compiler_support)
[![Platform](https://img.shields.io/static/v1?label=platform&message=Linux%20(Proton)%20%7C%20Windows&color=dimgray&style=flat)](#)
[![License](https://img.shields.io/static/v1?label=license&message=GPLv3&color=blue&style=flat)](LICENSE)

KCSE is a native plugin framework for **Kingdom Come: Deliverance 1**, in the same spirit as SKSE for Skyrim. It lets modders write C++ plugins that hook into game events, run code every frame, and call game functions directly — instead of being limited to what the game's own scripting supports.

It installs as a single `dinput8.dll` — no exe patching, no ASI loader, no repacking. This build runs on **Linux via Wine/Proton** (and still works on native Windows).

## Installation

1. Grab `dinput8.dll` and `kcd_addresslib_steam_404-504czj4.bin` from the [latest release](../../releases/latest).
2. Copy `dinput8.dll` to `<game>/Bin/Win64/`.
3. Copy `kcd_addresslib_steam_404-504czj4.bin` to `<game>/KCSE/addresslib/`.
4. Launch the game as usual. That's it — no other setup required.

This currently supports **Steam, game version 1.9.7.0** (build `404-504czj4`). Other versions/distributions aren't mapped yet — see [Address Library](#address-library) below if you want to add support for yours. On any other build, KCSE fails loudly with a clear dialog ("Address library not found" / "REL::ID N is not present") rather than silently running with wrong addresses — a crash on launch almost always means a version mismatch, not a corrupt install.

To install a plugin, drop its DLL into `<game>/KCSE/Plugins/` (or `<game>/mods/<modname>/KCSE/Plugins/` if you're using a mod manager).

## Building from source

**Linux:**

```sh
git clone --recursive https://github.com/ThisIsAkill/KCSE-kcd1_linux.git
cd KCSE-kcd1_linux
./build.sh
```

This cross-compiles `dinput8.dll` with MinGW-w64 — no Windows or Visual Studio needed. The DLL is produced at `build-mingw/dinput8.dll`.

```sh
cp build-mingw/dinput8.dll ~/.steam/steam/steamapps/common/KingdomComeDeliverance/Bin/Win64/
```

`dev-cycle.sh` wraps build, deploy, and verification into one loop:

```sh
./dev-cycle.sh          # build + Wine smoke test (fast, no game)
./dev-cycle.sh --game   # build + deploy + full game launch via Steam, watches KCSE.log
```

(`GAME_DIR` overrides the default Steam install path.)

Requires `mingw-w64` (`sudo apt install mingw-w64`); `wine` is only needed for the smoke test.

**Windows:**

```sh
git submodule update --init
cmake -B build -DCMAKE_TOOLCHAIN_FILE=<path-to-vcpkg>/scripts/buildsystems/vcpkg.cmake
cmake --build build --config Release
```

Requires Visual Studio 2022+ ("Desktop development with C++") and [vcpkg](https://github.com/microsoft/vcpkg). The DLL is produced at `build/Release/dinput8.dll`.

## How it works

`dinput8.dll` takes the place of the game's real `dinput8.dll` — Windows loads it automatically at startup since it sits next to the game's executable. KCSE's proxy forwards every DirectInput call through to the real system library so input works exactly as before, then in the background it:

1. Waits for the core CryEngine subsystems to be ready.
2. Installs its hooks into the game's engine.
3. Loads every plugin DLL and hands each one an API interface.
4. Dispatches lifecycle events (`DataLoaded`, `NewGame`, `LoadGame`, `SaveGame`, `AllPluginsLoaded`) as the game reaches each stage.

CryEngine's internal memory addresses shift between game builds, so KCSE never hardcodes them in plugin code — it resolves them at runtime through an **address library**, keyed to the exact build of the game you're running.

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

- Available lifecycle messages: `DataLoaded`, `LoadGame`, `SaveGame`, `NewGame`, `AllPluginsLoaded`.
- Per-frame tasks via `KCSE::GetTaskInterface()->AddTask(fn)`.
- Trampoline hooking via `KCSE::GetTrampoline()`.

## Address Library

Since the game's internal addresses aren't fixed, plugins ask for a symbolic ID and KCSE looks up the real address for whatever build is running — the same plugin binary keeps working across game patches as long as a mapping exists for that build.

Mappings are plain text files at `addresslib/mappings/<distribution>_<build_key>.txt`, one `<id> <hex offset>` pair per line. They're compiled into the binary format the game loads with:

```sh
python3 addresslib/gen_addresslib.py <game>/KCSE/addresslib addresslib/mappings/steam_<build_key>.txt
```

`dev-cycle.sh --game` does this automatically. If you're on a game version this repo doesn't have a mapping for yet, contributions adding one are welcome.

If a plugin crashes with `REL::ID N is not present in the address library for this version`, don't hand-search libKCD1's headers for it — run:

```sh
python3 addresslib/resolve_id.py N
```

It looks `N` up in libKCD1's `Offsets_RTTI.h`/`Offsets_VTABLE.h` (which embed each id's address in a comment), adds it to the mapping file, and re-sorts it. Pass `--game-dir <path>` to also recompile the `.bin` in the same step. It covers the common case — a plugin's `kcd_cast<>` or vtable hook needing an id nobody's mapped yet; if it can't find one, it tells you why and where to look instead.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | KCSE core: DLL proxy, plugin manager, event dispatcher, task interface, trampoline glue |
| `extern/libKCD1/` | [libKCD1](https://github.com/JerryYOJ/libKCD1), the reverse-engineered game headers KCSE builds against |
| `addresslib/` | Address-library mappings, the generator that compiles them, and `resolve_id.py` for filling in a missing `REL::ID` |
| `cmake/` | CMake helpers, including the MinGW-w64 cross-compilation toolchain file |
| `test/` | Minimal Wine smoke test, no game installation required |
| `build.sh` / `dev-cycle.sh` | Linux build and build-test-deploy scripts |

## Acknowledgments

This is a Linux port of [JerryYOJ](https://github.com/JerryYOJ)'s **[KCSE](https://github.com/JerryYOJ/KCSE-for-kcd1)**, built on their **[libKCD1](https://github.com/JerryYOJ/libKCD1)** reverse-engineering work. All credit for the original script extender design and the reverse-engineered game internals it depends on goes to them — this fork's contribution is getting it running on Linux via Wine/Proton.

Parts of this port (build fixes, debugging, and documentation) were done with AI assistance.

## Contributing

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before opening issues or pull requests.

## License

[GPLv3](LICENSE)
