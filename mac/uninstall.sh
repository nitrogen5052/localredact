#!/bin/bash
# Remove localredact. Keeps your always-redact list unless --all is given.
set -euo pipefail
home="${LOCALREDACT_HOME:-$HOME/.local/share/localredact}"
app_dir="${APP_DIR:-$HOME/Applications}"
rm -rf "$app_dir/localredact.app" "$home"
rm -rf "$HOME/.cache/huggingface/hub/models--mlx-community--openai-privacy-filter-bf16"
[ "${1:-}" = --all ] && rm -f "$app_dir/localredact — Always redact.txt"
echo "localredact removed."
