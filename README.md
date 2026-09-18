# Cryhook

[![C++17](https://img.shields.io/static/v1?label=standard&message=C%2B%2B17&color=blue&logo=c%2B%2B&logoColor=white&style=flat)](https://en.cppreference.com/w/cpp/compiler_support)
[![Platform](https://img.shields.io/static/v1?label=platform&message=Linux%20(Proton)%20%7C%20Windows&color=dimgray&style=flat)](#)
[![License](https://img.shields.io/static/v1?label=license&message=GPLv3&color=blue&style=flat)](LICENSE)

A Linux/Proton port of **KCSE** (Kingdom Come Script Extender) — [JerryYOJ](https://github.com/JerryYOJ)'s native plugin framework for **Kingdom Come: Deliverance 1**, in the same spirit as SKSE for Skyrim. It lets modders write C++ plugins that hook into game events, run code every frame, and call game functions directly — instead of being limited to what the game's own scripting supports.

It installs as a single `dinput8.dll` — no exe patching, no repacking, and no separate ASI loader: Cryhook loads `.asi` mods natively itself, alongside its own KCSE plugins. This build runs on **Linux via Wine/Proton** (and still works on native Windows).

## Installation

1. Grab `dinput8.dll` and the `kcd_addresslib_<dist>_404-504czj4.bin` matching your storefront (`steam`, `gog`, or `epic`) from the [latest release](../../releases/latest).
2. Copy `dinput8.dll` to `<game>/Bin/Win64/`.
3. Copy the `.bin` to `<game>/KCSE/addresslib/`.
4. Launch the game as usual. That's it — no other setup required.

This currently supports **Steam, GOG, and Epic, game version 1.9.7.0** (build `404-504czj4`). Other versions aren't mapped yet — see [Address Library](#address-library) below if you want to add support for yours. On any other build, Cryhook fails loudly with a clear dialog ("Address library not found" / "REL::ID N is not present") rather than silently running with wrong addresses — a crash on launch almost always means a version mismatch, not a corrupt install.

To install a plugin, drop its DLL into `<game>/KCSE/Plugins/` (or `<game>/mods/<modname>/KCSE/Plugins/` if you're using a mod manager).

`.asi` mods work too — drop the `.asi` file straight into `<game>/Bin/Win64/` per that mod's own install instructions, same as you would with Ultimate ASI Loader. Cryhook already owns `dinput8.dll` for its own hooks, so it loads any `.asi` files it finds there itself; you don't need (and shouldn't run) a second ASI loader alongside it.

### Steam Deck / Desktop Mode

`<game>` above means the game's install folder. On Steam Deck (or any Linux Steam install) the easiest way to get there:

1. Switch to **Desktop Mode** (hold the Power button → *Switch to Desktop*). You need Desktop Mode to copy files — this can't be done from Gaming Mode.
2. In Steam, right-click **Kingdom Come: Deliverance** → **Properties → Installed Files → Browse...**. This opens the game's folder directly in the file manager (Dolphin), so you don't need to know or type the actual path.
3. Download `dinput8.dll` and `kcd_addresslib_steam_404-504czj4.bin` from the [latest release](../../releases/latest) using the desktop browser.
4. In the file manager: copy `dinput8.dll` into the `Bin\Win64` folder, and `kcd_addresslib_steam_404-504czj4.bin` into `KCSE\addresslib` (create the `KCSE` and `addresslib` folders if they don't exist yet).
5. Switch back to Gaming Mode and launch the game normally — no launch options, no forcing a specific Proton version, nothing else to configure.

To confirm it worked: open `<game>/KCSE/KCSE.log` in a text editor after launching. It should end with `Ready.`. If the game won't start at all (with or without Cryhook), that's a Proton/compatibility issue unrelated to this mod — check the game's own Properties → Compatibility tab first.

## Building from source

**Linux:**

```sh
git clone --recursive https://github.com/ThisIsAkill/cryhook-kcd1.git
cd cryhook-kcd1
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

`dinput8.dll` takes the place of the game's real `dinput8.dll` — Windows loads it automatically at startup since it sits next to the game's executable. Cryhook's proxy forwards every DirectInput call through to the real system library so input works exactly as before, then in the background it:

1. Waits for the core CryEngine subsystems to be ready.
2. Installs its hooks into the game's engine.
3. Loads every plugin DLL and hands each one an API interface.
4. Scans its own directory (`Bin/Win64/`) for `.asi` files and `LoadLibrary()`s each one — no export or version checking, they self-init in `DllMain` exactly as they would under a standalone ASI loader.
5. Dispatches lifecycle events (`DataLoaded`, `NewGame`, `LoadGame`, `SaveGame`, `AllPluginsLoaded`) as the game reaches each stage.

CryEngine's internal memory addresses shift between game builds, so Cryhook never hardcodes them in plugin code — it resolves them at runtime through an **address library**, keyed to the exact build of the game you're running.

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

Since the game's internal addresses aren't fixed, plugins ask for a symbolic ID and Cryhook looks up the real address for whatever build is running — the same plugin binary keeps working across game patches as long as a mapping exists for that build.

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

### Optional: upstream address library

The hand-maintained mappings above are enough to build and run Cryhook, but they're a small, unverified subset — good enough to unblock a specific plugin, not a complete map of the binary. [JerryYOJ](https://github.com/JerryYOJ) (the original KCSE/libKCD1 author) separately maintains [Address-Library-For-KCSE](https://github.com/JerryYOJ/Address-Library-For-KCSE), a much larger table (700k+ entries) built by diffing the Steam/GOG/Epic binaries directly in IDA. It uses the same id numbering and the same `.bin` format Cryhook loads, so nothing needs converting.

It's not fetched by default — it's a large, separately-owned repository with no license file, so this project neither vendors its data nor pulls it into a routine clone/build. If you want the fuller table anyway:

```sh
git submodule update --init extern/addresslib-kcse
```

`gen_addresslib.py` then picks it up automatically: for any build key it has an upstream `.bin` for, that table becomes the base, and this repo's own `mappings/*.txt` entries are layered on top and win on conflict. Build keys upstream doesn't cover still compile from local mappings alone, exactly as before. Nothing under `extern/addresslib-kcse/` is committed to this repo — it's your own checkout of JerryYOJ's repository, governed by its own terms.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | Cryhook core: DLL proxy, plugin manager, `.asi` loader, event dispatcher, task interface, trampoline glue |
| `extern/libKCD1/` | [libKCD1](https://github.com/JerryYOJ/libKCD1), the reverse-engineered game headers KCSE builds against |
| `extern/addresslib-kcse/` | Optional, not fetched by default — [Address-Library-For-KCSE](https://github.com/JerryYOJ/Address-Library-For-KCSE), see [Address Library](#address-library) |
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
