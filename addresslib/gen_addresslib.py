#!/usr/bin/env python3
"""Compile human-editable address-library mapping files into the binary
format REL::IDDatabase (extern/libKCD1/src/REL/IDDatabase.cpp) loads at
runtime from <game_root>/KCSE/addresslib/.

Mapping files live in addresslib/mappings/<dist>_<build_key>.txt, one
"<id> <hex offset>" pair per line (# comments and blank lines ignored).
Each produces kcd_addresslib_<dist>_<build_key>.bin.

If the optional extern/addresslib-kcse submodule (JerryYOJ's
Address-Library-For-KCSE, not fetched by default -- see README) is checked
out, its precompiled kcd_addresslib_<dist>_<build_key>.bin files are used as
a base layer for the matching key: this repo's own mappings/*.txt entries are
layered on top and win on conflict, since those are the ones this port has
hand-verified. A build key that only exists upstream is compiled as-is; one
that only exists locally is compiled as before, unaffected by the submodule's
absence.

Usage:
    gen_addresslib.py <output_dir> [mapping_file ...]

With no mapping_file arguments, every key found in addresslib/mappings/*.txt
and (if present) the upstream submodule is compiled.
"""
import struct
import sys
from pathlib import Path

DIST_IDS = {"steam": 1, "gog": 2, "epic": 3}
FORMAT_VERSION = 1
MAGIC = b"KASL"

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = REPO_ROOT / "extern/addresslib-kcse/kcd1_address_library"


def parse_key(stem: str) -> tuple[str, str]:
    dist_name, _, build_key = stem.partition("_")
    if not build_key or dist_name not in DIST_IDS:
        raise ValueError(
            f"{stem}: expected '<dist>_<build_key>' with dist one of {sorted(DIST_IDS)}"
        )
    return dist_name, build_key


def load_text_mapping(src: Path) -> dict[int, int]:
    entries = {}
    for lineno, raw in enumerate(src.read_text().splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"{src}:{lineno}: expected '<id> <hex offset>', got: {raw!r}")
        id_, offset = parts
        entries[int(id_, 0)] = int(offset, 0)
    return entries


def load_upstream_bin(dist_name: str, build_key: str) -> dict[int, int]:
    """Reads a precompiled KASL .bin from the optional upstream submodule, if
    present. Returns {} if the submodule isn't checked out or has no matching
    build key -- callers don't need to special-case its absence."""
    path = UPSTREAM_DIR / f"kcd_addresslib_{dist_name}_{build_key}.bin"
    if not path.exists():
        return {}

    data = path.read_bytes()
    if data[:4] != MAGIC:
        raise ValueError(f"{path}: bad magic, expected {MAGIC!r}")
    version, dist_id, count = struct.unpack_from("<III", data, 4)
    if version != FORMAT_VERSION:
        raise ValueError(f"{path}: unsupported format version {version}")
    if dist_id != DIST_IDS[dist_name]:
        raise ValueError(f"{path}: dist id {dist_id} doesn't match {dist_name!r} filename")

    entries = {}
    off = 16
    for _ in range(count):
        id_, offset = struct.unpack_from("<II", data, off)
        entries[id_] = offset
        off += 8
    return entries


def write_bin(dist_name: str, build_key: str, entries: dict[int, int], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"kcd_addresslib_{dist_name}_{build_key}.bin"
    with out_path.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<III", FORMAT_VERSION, DIST_IDS[dist_name], len(entries)))
        for id_ in sorted(entries):
            f.write(struct.pack("<II", id_, entries[id_]))
    return out_path


def compile_mapping(src: Path, out_dir: Path) -> Path:
    dist_name, build_key = parse_key(src.stem)
    entries = load_upstream_bin(dist_name, build_key)
    local = load_text_mapping(src)
    if entries and local:
        print(f"    ({len(entries)} upstream + {len(local)} local, local wins on conflict)")
    entries.update(local)
    return write_bin(dist_name, build_key, entries, out_dir)


def compile_upstream_only(dist_name: str, build_key: str, out_dir: Path) -> Path:
    entries = load_upstream_bin(dist_name, build_key)
    return write_bin(dist_name, build_key, entries, out_dir)


def main(argv: list[str]) -> int:
    if len(argv) < 1:
        print(__doc__)
        return 2
    out_dir = Path(argv[0])
    mapping_files = [Path(p) for p in argv[1:]]

    if mapping_files:
        for src in mapping_files:
            out_path = compile_mapping(src, out_dir)
            print(f"wrote {out_path}")
        return 0

    # Auto-discover: every local mapping, plus any upstream-only build key.
    mappings_dir = Path(__file__).parent / "mappings"
    local_files = sorted(mappings_dir.glob("*.txt"))
    local_keys = {f.stem for f in local_files}

    for src in local_files:
        out_path = compile_mapping(src, out_dir)
        print(f"wrote {out_path}")

    if UPSTREAM_DIR.is_dir():
        for bin_path in sorted(UPSTREAM_DIR.glob("kcd_addresslib_*.bin")):
            stem = bin_path.stem.removeprefix("kcd_addresslib_")
            if stem in local_keys:
                continue  # already compiled above, local mapping merged in
            dist_name, build_key = parse_key(stem)
            out_path = compile_upstream_only(dist_name, build_key, out_dir)
            print(f"wrote {out_path} (upstream-only)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
