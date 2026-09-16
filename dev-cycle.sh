#!/usr/bin/env bash
# dev-cycle.sh — build → (smoke | game) → report
#
# Usage:
#   ./dev-cycle.sh          # build + Wine smoke test (fast, no game)
#   ./dev-cycle.sh --game   # build + deploy + full game launch (slow)
#
# GAME_DIR env var overrides the default Steam path.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build-mingw"
GAME_DIR="${GAME_DIR:-$HOME/.steam/steam/steamapps/common/KingdomComeDeliverance}"
BIN_DIR="$GAME_DIR/Bin/Win64"
LOG_FILE="$GAME_DIR/KCSE/KCSE.log"
STEAM_APP_ID=379430
MODE="${1:-}"

die()  { echo "[FAIL] $*" >&2; exit 1; }
pass() { echo "[PASS] $*"; }

# ── 1. Build ──────────────────────────────────────────────────────────────────
echo "==> Building..."
cmake --build "$BUILD_DIR" --parallel 2>&1 || die "Build failed — fix compile errors above"
echo "    dinput8.dll OK"

# ── 2a. Smoke test (default) ──────────────────────────────────────────────────
if [ "$MODE" != "--game" ]; then
    echo "==> Running Wine smoke test..."
    cmake --build "$BUILD_DIR" --target smoke_test 2>&1
    exit $?
fi

# ── 2b. Full game cycle ───────────────────────────────────────────────────────
echo "==> Deploying to $BIN_DIR ..."
[ -d "$BIN_DIR" ] || die "Game not found at $GAME_DIR — set GAME_DIR env var"
cp "$BUILD_DIR/dinput8.dll" "$BIN_DIR/"

echo "==> Compiling address library..."
python3 "$SCRIPT_DIR/addresslib/gen_addresslib.py" "$GAME_DIR/KCSE/addresslib" \
    || die "Address library generation failed"

# Clear old log
rm -f "$LOG_FILE"
mkdir -p "$GAME_DIR/KCSE"

echo "==> Launching game (Steam app $STEAM_APP_ID)..."
steam "steam://rungameid/$STEAM_APP_ID" > /dev/null 2>&1 &

# Wait for game process (up to 60s)
echo "==> Waiting for game process..."
for i in $(seq 1 30); do
    pgrep -fi "KingdomCome.exe" > /dev/null 2>&1 && break
    sleep 2
    [ $i -eq 30 ] && die "Game didn't start after 60s"
done
echo "    Game process found"

# Watch log for Ready. or [error] (up to 300s; CryEngine cold loads under
# Wine/DXVK can take a while to compile shaders on first launch)
echo "==> Watching KCSE.log..."
RESULT="timeout"
for i in $(seq 1 150); do
    sleep 2
    if [ -f "$LOG_FILE" ]; then
        if grep -q "Ready\." "$LOG_FILE"; then
            RESULT="pass"; break
        fi
        if grep -qi "\[error\]\|\[critical\]" "$LOG_FILE"; then
            RESULT="error"; break
        fi
    fi
    if ! pgrep -fi "KingdomCome.exe" > /dev/null 2>&1; then
        RESULT="crashed"; break
    fi
done

# Kill game
echo "==> Stopping game..."
pkill -fi "KingdomCome.exe" 2>/dev/null || true
sleep 3
pkill -9 -fi "KingdomCome.exe" 2>/dev/null || true

# Report
echo ""
echo "── KCSE.log ──────────────────────────────────────────"
[ -f "$LOG_FILE" ] && cat "$LOG_FILE" || echo "(no log written)"
echo "──────────────────────────────────────────────────────"

if [ "$RESULT" = "pass" ]; then
    pass "KCSE initialized successfully"
    exit 0
else
    die "Result: $RESULT"
fi
