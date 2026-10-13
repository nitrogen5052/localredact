#!/bin/bash
# Install localredact: Python environment, model (~2.8 GB), and the localredact app.
# Overridable: LOCALREDACT_HOME (environment), APP_DIR (where the app and list go), OUT_DIR (results).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(dirname "$here")"
home="${LOCALREDACT_HOME:-$HOME/.local/share/localredact}"
app_dir="${APP_DIR:-$HOME/Applications}"
out_dir="${OUT_DIR:-$HOME/Downloads}"
app="$app_dir/localredact.app"
list="$app_dir/localredact — Always redact.txt"

[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || { echo "localredact needs a Mac with Apple silicon."; exit 1; }
command -v uv >/dev/null || { echo "Install uv first: brew install uv"; exit 1; }

echo "1/3 Python environment → $home/venv"
uv venv -q --allow-existing --python 3.12 "$home/venv"
uv pip install -q --python "$home/venv/bin/python" -r "$here/requirements.txt"

echo "2/3 Model (first time ~2.8 GB) → Hugging Face cache"
"$home/venv/bin/python" -I -c "
from huggingface_hub import snapshot_download
snapshot_download('mlx-community/openai-privacy-filter-bf16', revision='c855bd1412b817aa24a29847f7877a4389bb5ce7')"

echo "3/3 App → $app"
mkdir -p "$app_dir"
rm -rf "$app"
osacompile -o "$app" "$here/localredact.applescript"
res="$app/Contents/Resources"
cp "$here/redact.sh" "$here/engine_mlx.py" "$repo/core/redact_core.py" "$res/"
cp -R "$here/opf_checkpoint" "$res/"
cat > "$res/paths.sh" <<PATHS
PYTHON="$home/venv/bin/python"
LIST="$list"
OUT_DIR="$out_dir"
LOG="$HOME/Library/Logs/localredact.log"
PATHS
[ -e "$list" ] || cp "$repo/always-redact.example.txt" "$list"

echo
echo "Done. Open $app (add it to your Dock) and choose files to redact."
echo "Words that must always be removed (your name, street…): $list"
