#!/usr/bin/env bash
# Checks this machine and proves the studio works. Linux, macOS, Termux, Git Bash/WSL.
# Installs nothing system-wide: it only tells you what is missing. Safe to run repeatedly.
set -u
cd "$(dirname "$0")/.."

say() { printf '%s\n' "$*"; }
fail=0

# --- python >= 3.9
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then PY=$c; break; fi
done
if [ -z "$PY" ]; then
  say "MISSING: Python 3.9 or newer."
  say "  Debian/Ubuntu: sudo apt install python3 | macOS: brew install python | Termux: pkg install python | Windows: use scripts/install.ps1"
  fail=1
else
  say "python: $($PY --version 2>&1)"
fi

# --- ffmpeg + ffprobe
for t in ffmpeg ffprobe; do
  if command -v "$t" >/dev/null 2>&1; then say "$t: found"; else say "MISSING: $t"; fail=1; fi
done
if ! command -v ffmpeg >/dev/null 2>&1; then
  say "  Debian/Ubuntu: sudo apt install ffmpeg | macOS: brew install ffmpeg | Termux: pkg install ffmpeg"
fi

[ "$fail" -eq 0 ] || { say ""; say "Install the missing pieces above, then run this script again."; exit 1; }

say ""
say "Running the self-test (renders a tiny mock movie, checks it has video AND audio)..."
"$PY" -m movie_studio selftest || { say "Self-test failed. See docs/INSTALL.md, Troubleshooting."; exit 1; }

say ""
say "Done. The studio works on this machine."
say "  Try it:        $PY -m movie_studio make \"\$(cat examples/idea.txt)\" --writer template --scenes 3"
say "  Text model:    ./scripts/pull_model.sh        (needs Ollama: https://ollama.com/download)"
say "  Real video:    docs/INSTALL.md, section 'Real video'"
