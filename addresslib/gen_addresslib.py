#!/usr/bin/env python3
"""Compile human-editable address-library mapping files into the binary
format REL::IDDatabase (extern/libKCD1/src/REL/IDDatabase.cpp) loads at
runtime from <game_root>/KCSE/addresslib/.

Mapping files live in addresslib/mappings/<dist>_<build_key>.txt, one
"<id> <hex offset>" pair per line (# comments and blank lines ignored).
Each produces kcd_addresslib_<dist>_<build_key>.bin.

Usage:
    gen_addresslib.py <output_dir> [mapping_file ...]

With no mapping_file arguments, every *.txt under addresslib/mappings/ is
compiled.
"""
import struct
import sys
from pathlib import Path

DIST_IDS = {"steam": 1, "gog": 2, "epic": 3}
FORMAT_VERSION = 1
MAGIC = b"KASL"


def compile_mapping(src: Path, out_dir: Path) -> Path:
    stem = src.stem  # "<dist>_<build_key>"
    dist_name, _, build_key = stem.partition("_")
    if not build_key or dist_name not in DIST_IDS:
        raise ValueError(
            f"{src}: filename must be '<dist>_<build_key>.txt' with dist one "
            f"of {sorted(DIST_IDS)}"
        )

    entries = []
    for lineno, raw in enumerate(src.read_text().splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"{src}:{lineno}: expected '<id> <hex offset>', got: {raw!r}")
        id_, offset = parts
        entries.append((int(id_, 0), int(offset, 0)))

    entries.sort(key=lambda e: e[0])

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"kcd_addresslib_{dist_name}_{build_key}.bin"
    with out_path.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<III", FORMAT_VERSION, DIST_IDS[dist_name], len(entries)))
        for id_, offset in entries:
            f.write(struct.pack("<II", id_, offset))
    return out_path


def main(argv: list[str]) -> int:
    if len(argv) < 1:
        print(__doc__)
        return 2
    out_dir = Path(argv[0])
    mapping_files = [Path(p) for p in argv[1:]]
    if not mapping_files:
        mapping_files = sorted((Path(__file__).parent / "mappings").glob("*.txt"))

    for src in mapping_files:
        out_path = compile_mapping(src, out_dir)
        print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
