#!/bin/bash
# Redact one file with OpenAI Privacy Filter (Apple GPU via MLX); write "<name> (redacted).txt" to OUT_DIR.
# Prints the output path on success; exits non-zero with a message on failure.
# paths.sh (written by install.sh) sets PYTHON, LIST, OUT_DIR and LOG.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
source "$here/paths.sh"
exec 2>>"$LOG"; echo "--- $(date) $1" >&2
in="$1"
name="$(basename "$in")"; base="${name%.*}"; ext="$(echo "${name##*.}" | tr '[:upper:]' '[:lower:]')"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
txt="$tmp/input.txt"

case "$ext" in
  txt|md|csv|tsv|json|log|text) cp "$in" "$txt" ;;
  docx|doc|rtf|rtfd|odt|html|htm|webarchive) textutil -convert txt -output "$txt" "$in" >/dev/null ;;
  pdf) osascript -l JavaScript -e 'function run(a){ObjC.import("PDFKit");var d=$.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(a[0]));if(!d||d.isNil())throw "Could not open PDF";var s=d.string;return (s&&!s.isNil())?s.js:"";}' "$in" > "$txt" ;;
  *) echo "Unsupported file type: .$ext (use txt, md, csv, docx, rtf, html or pdf)"; exit 2 ;;
esac

if [ ! -s "$txt" ] || ! grep -q '[^[:space:]]' "$txt"; then
  echo "No text found in $name (a scanned PDF has images, not text)."; exit 3
fi

out="$OUT_DIR/$base (redacted).txt"
n=2; while [ -e "$out" ]; do out="$OUT_DIR/$base (redacted $n).txt"; n=$((n+1)); done

if ! "$PYTHON" -I "$here/engine_mlx.py" "$txt" "$tmp/out.txt" "$LIST" 2> "$tmp/err.txt"; then
  cat "$tmp/err.txt" >&2
  echo "localredact failed on $name:"; tail -3 "$tmp/err.txt"; exit 4
fi
mv "$tmp/out.txt" "$out"
echo "$out"
