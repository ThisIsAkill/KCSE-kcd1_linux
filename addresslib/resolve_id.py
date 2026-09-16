#!/usr/bin/env python3
"""Resolve a "REL::ID N is not present" crash to its offset and add it to a
mapping file, without hand-searching libKCD1's headers for it.

When a plugin hits this crash, N is almost always either an RTTI type
descriptor (needed by a kcd_cast<>) or a vtable slot (needed by a hook) that
nobody has mapped for this game build yet. Both kinds carry their Steam-RVA
right there in libKCD1's HEAD headers:

  - Offsets_RTTI.h: `inline constexpr ::REL::ID RTTI_X { N };  // 0xHEX ...`
  - Offsets_VTABLE.h: an array of ids with one "@ WHGame+0xHEX" per slot in
    the comment block above it.

This script greps those two files for N, and if found, appends "<N> <hex>"
to the mapping file and re-sorts it -- the same thing a human would do by
hand, minus the hand part.

Ids that instead come from a *function* or *singleton* offset (declared in
Offsets.cpp/S_GameContext.cpp/etc., REL::ID(N) with no RVA in the current
header) aren't resolvable this way: that family of offset predates the
address-library migration and only exists in libKCD1 commit 60573fc^'s
include/Offsets/Offsets.h, as a k*Offset constant matched by cross-referencing
the sub_18XXXXXXX address in its call site's comment. See the mapping file's
own header comment for how the existing entries of that kind were derived.

Usage:
    addresslib/resolve_id.py <id> [<id> ...] [--dist steam] [--build 404-504czj4]
                              [--libkcd1 PATH] [--game-dir PATH]

Examples:
    addresslib/resolve_id.py 123 141
    addresslib/resolve_id.py 187 --game-dir ~/.steam/.../KingdomComeDeliverance/KCSE/addresslib
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

RTTI_PAT = re.compile(
    r"::REL::ID\s+(\w+)\s*\{\s*(\d+)\s*\}\s*;\s*//\s*(0x[0-9A-Fa-f]+)\s*(.*)"
)
VTABLE_ARRAY_PAT = re.compile(
    r"((?:^//.*\n)+)^inline constexpr std::array<::REL::ID,\s*\d+>\s*(\w+)\{([^}]*)\};",
    re.MULTILINE,
)
VTABLE_ID_PAT = re.compile(r"::REL::ID\((\d+)\)")
VTABLE_ADDR_PAT = re.compile(r"@\s*WHGame\+(0x[0-9A-Fa-f]+)")


def find_rtti(libkcd1: Path, id_: int):
    path = libkcd1 / "include/Offsets/Offsets_RTTI.h"
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        m = RTTI_PAT.search(line)
        if m and int(m.group(2)) == id_:
            name, _, offset, desc = m.groups()
            desc = desc.strip()
            label = f"{name} RTTI type descriptor" + (f" ({desc})" if desc else "")
            return int(offset, 16), label
    return None


def find_vtable(libkcd1: Path, id_: int):
    path = libkcd1 / "include/Offsets/Offsets_VTABLE.h"
    if not path.exists():
        return None
    text = path.read_text()
    for comment, name, idlist in VTABLE_ARRAY_PAT.findall(text):
        ids = [int(x) for x in VTABLE_ID_PAT.findall(idlist)]
        addrs = VTABLE_ADDR_PAT.findall(comment)
        if id_ in ids and len(addrs) == len(ids):
            idx = ids.index(id_)
            return int(addrs[idx], 16), f"{name}[{idx}] vtable"
    return None


def resolve(libkcd1: Path, id_: int):
    return find_rtti(libkcd1, id_) or find_vtable(libkcd1, id_)


def load_mapping(path: Path):
    """Returns (header_lines, {id: raw_line}). Existing lines are kept as-is;
    only newly resolved ids get freshly formatted lines."""
    header = []
    entries = {}
    if path.exists():
        for line in path.read_text().splitlines():
            stripped = line.split("#", 1)[0].strip()
            if not stripped:
                if not entries:
                    header.append(line)
                continue
            parts = stripped.split()
            if len(parts) == 2:
                entries[int(parts[0], 0)] = line
    return header, entries


def main(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("ids", nargs="+", type=int, help="REL::ID value(s) from the crash dialog")
    ap.add_argument("--dist", default="steam", help="steam / gog / epic (default: steam)")
    ap.add_argument("--build", default="404-504czj4", help="build key (default: 404-504czj4)")
    ap.add_argument("--libkcd1", default=None, help="path to the libKCD1 checkout (default: extern/libKCD1)")
    ap.add_argument("--game-dir", default=None, help="also recompile the .bin into <game>/KCSE/addresslib")
    args = ap.parse_args(argv)

    libkcd1 = Path(args.libkcd1) if args.libkcd1 else REPO_ROOT / "extern/libKCD1"
    if not (libkcd1 / "include/Offsets/Offsets_RTTI.h").exists():
        print(
            f"error: no libKCD1 checkout at {libkcd1} "
            f"(pass --libkcd1, or `git submodule update --init`)",
            file=sys.stderr,
        )
        return 2

    mapping_path = REPO_ROOT / "addresslib/mappings" / f"{args.dist}_{args.build}.txt"
    header, entries = load_mapping(mapping_path)

    resolved = 0
    unresolved = []
    for id_ in args.ids:
        if id_ in entries:
            print(f"id {id_}: already mapped -- {entries[id_].strip()}")
            continue
        hit = resolve(libkcd1, id_)
        if not hit:
            unresolved.append(id_)
            continue
        offset, desc = hit
        entries[id_] = f"{id_:<4}0x{offset:X}   # {desc}"
        resolved += 1
        print(f"id {id_}: resolved -- {desc} @ 0x{offset:X}")

    if resolved:
        lines = header + [entries[k] for k in sorted(entries)]
        mapping_path.write_text("\n".join(lines) + "\n")
        print(f"wrote {resolved} new entr{'y' if resolved == 1 else 'ies'} to {mapping_path}")

        if args.game_dir:
            gen = SCRIPT_DIR / "gen_addresslib.py"
            subprocess.run(
                [sys.executable, str(gen), args.game_dir, str(mapping_path)], check=True
            )

    if unresolved:
        ids_str = ", ".join(str(i) for i in unresolved)
        print(
            f"\nid(s) {ids_str}: not found in Offsets_RTTI.h / Offsets_VTABLE.h at libKCD1 HEAD.\n"
            f"This usually means it's a function/singleton offset (Offsets.cpp-style), which\n"
            f"doesn't carry its RVA at HEAD. Cross-reference libKCD1 commit 60573fc^'s\n"
            f"include/Offsets/Offsets.h for a k*Offset constant whose call-site comment matches\n"
            f"the id's usage, the way the pre-RTTI entries in {mapping_path.name} were derived.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
