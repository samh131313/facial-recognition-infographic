#!/bin/bash
# Run this in a PythonAnywhere Bash console. It packs everything Liquidity needs into
#   ~/liquidity-export.tar.gz
# which you then download from the PythonAnywhere "Files" page on your main PC.
set -euo pipefail
cd ~
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

# Consistent copies of the databases even if the site is running.
for db in chat.db gpt.db; do
  if [ -f ~/"$db" ]; then
    python3 - ~/"$db" "$STAGE/$db" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.execute("PRAGMA journal_mode=DELETE"); dst.close(); src.close()
PY
    echo "copied $db"
  fi
done
[ -f ~/.flask_session_key ] && cp ~/.flask_session_key "$STAGE/flask_session_key.txt"

ITEMS=()
for item in flask_app.py gpt_router.py requirements.txt secret.py media pages downloads minecraft_game fps_test; do
  [ -e ~/mysite/"$item" ] && ITEMS+=("$item")
done
echo "packing: ${ITEMS[*]}"

rm -f ~/liquidity-export.tar.gz
tar -czf ~/liquidity-export.tar.gz \
  --exclude='__pycache__' --exclude='.owner-uploads' \
  -C "$STAGE" . \
  -C ~/mysite "${ITEMS[@]}"

ls -lh ~/liquidity-export.tar.gz
echo "Done. Download liquidity-export.tar.gz from the Files page (home folder)."
