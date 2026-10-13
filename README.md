# localredact

Open the app, pick a document, and get a copy with names, emails, phone numbers, addresses,
account numbers and dates replaced by labels. Runs entirely on your own computer (Mac or
Windows). Nothing is uploaded.

```
Statement for JOHN Q. EXAMPLE           →   Statement for <PRIVATE_PERSON>
Call Jane Doe at 555-123-4567            →   Call <PRIVATE_PERSON> at <PRIVATE_PHONE>
```

Typical use: clean a bank statement, medical letter or contract **before** you paste it
into ChatGPT, Claude or anything else online.

## Why this exists

OpenAI released [Privacy Filter](https://github.com/openai/privacy-filter), a small
open-weight model that labels personal information. Using it as-is is awkward:

1. **It won't run in LM Studio or other chat apps.** It's a token classifier, not a chat
   model; chat apps crash on it (`'Model' object has no attribute 'get_input_embeddings'`).
2. **On a Mac the reference tool runs on the CPU.** A ~51 KB bank statement took about
   8 minutes on an M4 MacBook Air.
3. **It's a command-line tool.** No file picker, no PDF or Word support.

And one accuracy problem: it **misses names written in ALL CAPS**, which is exactly how
bank statements print the account holder.

| | OpenAI reference (Mac CPU) | localredact on Mac (MLX, GPU) |
|---|---|---|
| ~51 KB bank statement, M4 MacBook Air 16 GB | ~8 min¹ | ~20 s |
| Account holder's ALL-CAPS name left visible | 12 lines | 0 lines |
| Interface | terminal | app with a file picker; PDF, Word, text |

¹ That CPU run overlapped with another job for part of the time; treat it as "minutes", not an exact figure.

## Platforms

| | Mac | Windows |
|---|---|---|
| Requires | Apple silicon (M1 or later) | Windows 10/11, 64-bit |
| Model runs on | Apple GPU via [MLX](https://github.com/ml-explore/mlx) | NVIDIA GPU via CUDA if present, otherwise CPU (works; long files take minutes) |
| File picker | Finder | File Explorer |
| Inputs | .txt .md .csv .docx .doc .rtf .html .pdf | .txt .md .csv .docx .html .pdf |
| Status | Tested | **New: tested on a Mac running the Windows code; first real Windows test pending** |

Output is always plain text, `<name> (redacted).txt` in your Downloads folder.
Text-based PDFs only; scanned pages contain images, not text, and are rejected.

## Install: Mac

Needs [uv](https://docs.astral.sh/uv/) (`brew install uv`) and ~4 GB free.

```bash
git clone https://github.com/nitrogen5052/localredact && cd localredact
bash mac/install.sh
```

No git? On GitHub choose **Code → Download ZIP**, unzip, open Terminal in that folder and
run `bash mac/install.sh`. The first install downloads ~4 GB and takes a few minutes; after
that it works offline.

| What | Where |
|---|---|
| App | `~/Applications/localredact.app`; add it to your Dock |
| Your always-redact list | `~/Applications/localredact — Always redact.txt` |
| Python environment | `~/.local/share/localredact/` |
| Model (2.8 GB) | `~/.cache/huggingface/` |
| Log (file paths and errors only, never content) | `~/Library/Logs/localredact.log` |

The list sits next to the app because macOS blocks apps from reading ~/Documents without
a permission grant. Uninstall: `bash mac/uninstall.sh` (add `--all` to also delete your list).

## Install: Windows

Needs uv (`winget install --id=astral-sh.uv -e`, then open a new PowerShell window) and
~6 GB free (more with an NVIDIA GPU, because the CUDA build of PyTorch is larger).

```powershell
git clone https://github.com/nitrogen5052/localredact; cd localredact
powershell -ExecutionPolicy Bypass -File windows\install.ps1
```

No git? **Code → Download ZIP**, unzip, open PowerShell in that folder and run the second line.
The installer picks the GPU build of PyTorch automatically when it finds an NVIDIA driver,
and prints whether it will run on the GPU or the CPU.

| What | Where |
|---|---|
| App | Start menu → **localredact**, and a desktop shortcut |
| Your always-redact list | Start menu → localredact → **Edit always-redact list** (`%LOCALAPPDATA%\localredact\Always redact.txt`) |
| Python environment and app files | `%LOCALAPPDATA%\localredact\` |
| Model (2.8 GB) | `%USERPROFILE%\.cache\huggingface\` |
| Log (file paths and errors only, never content) | `%LOCALAPPDATA%\localredact\localredact.log` |

Uninstall: `powershell -ExecutionPolicy Bypass -File windows\uninstall.ps1` (add `-All` to
also delete your list).

## Use

Open the app and choose one or more files (the picker starts in Downloads). A progress
window shows; results open when done. On a Mac or an NVIDIA GPU, expect 15–30 seconds per file.

**Add your own name to the always-redact list.** The model misses some names, especially
unusual ones (in testing it missed "Dear Jane Testperson" but caught "Dear Jane Smith"). Anything
on the list is removed every time, in any capitalisation.

## How it works

- **OpenAI's own decoding.** Tokenization, the constrained Viterbi decoder and span logic are
  OpenAI's `opf` code on both platforms. Windows runs `opf` unchanged (plain-PyTorch path).
  The Mac swaps only the model's forward pass for the
  [MLX port](https://huggingface.co/mlx-community/openai-privacy-filter-bf16) (same bf16
  weights). On a 600-line synthetic ledger the Mac and reference pipelines differed on ~10% of
  lines (bf16 rounding, mostly date boundaries) and missed a similar number of names (4 vs 3).
- **Chunked to fit in memory (Mac).** Each layer looks ±128 tokens; 8 layers give 1024 tokens of
  context per side. Long documents run in 2048-token chunks with 1024-token margins, which
  matches a single full pass.
- **ALL-CAPS fix.** Lines in capitals are title-cased before the model reads them (same
  length, so positions map back exactly); the output keeps the original text.
- **Always-redact list.** Whole words, case-insensitive, any spacing between words. If the
  list exists but can't be read, the app stops with an error instead of producing output without it.

```
core/      shared logic: caps fix, always-redact list, span merging (both platforms)
mac/       MLX engine, AppleScript app, install.sh
windows/   PyTorch engine, PDF/Word reading, Tk app, install.ps1
tests/     fake data only
```

## Limits: read this

- **This reduces risk; it doesn't eliminate it.** OpenAI describes the model as a
  redaction and data-minimisation aid, not an anonymisation, compliance or safety
  guarantee. Read the output before you share it.
- Dollar amounts and partial card numbers ("ending 4242") are not personal data to the
  model and are left in.
- Formatting is lost; output is plain text.
- Not for HIPAA, GDPR or any other compliance use.

## Tests

```bash
python3 -m unittest discover -s tests                                   # core: standard library only
~/.local/share/localredact/venv/bin/python -m unittest discover -s tests # Mac, with the model
```

On Windows: `%LOCALAPPDATA%\localredact\venv\Scripts\python -m unittest discover -s tests`.
End-to-end model tests run when that platform's environment and model are installed.

## Status and roadmap

Early, personal tool made public. Planned:

- Own MLX implementation of the model (drop the `mlx-embeddings` dependency)
- Keep the original format (Word in → Word out)
- Optional review screen that highlights each redaction before saving

## License

GPL-3.0-or-later (see [LICENSE](LICENSE)), because the Mac GPU path uses
[mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) (GPL-3.0). Third-party
components and their licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Not affiliated with OpenAI.
