#!/bin/bash
# Remove redact-mac. Keeps your always-redact list unless --all is given.
set -euo pipefail
home="${REDACT_MAC_HOME:-$HOME/.local/share/redact-mac}"
app_dir="${APP_DIR:-$HOME/Applications}"
rm -rf "$app_dir/redact-mac.app" "$home"
rm -rf "$HOME/.cache/huggingface/hub/models--mlx-community--openai-privacy-filter-bf16"
[ "${1:-}" = --all ] && rm -f "$app_dir/redact-mac — Always redact.txt"
echo "redact-mac removed."
