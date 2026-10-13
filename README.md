# redact-mac

Open the app, pick a document in Finder, and get a copy with names, emails, phone numbers, addresses,
account numbers and dates replaced by labels. Runs entirely on your Mac's GPU.
Nothing is uploaded.

```
Statement for JOHN Q. EXAMPLE           →   Statement for <PRIVATE_PERSON>
Call Jane Doe at 555-123-4567            →   Call <PRIVATE_PERSON> at <PRIVATE_PHONE>
```

Typical use: clean a bank statement, medical letter or contract **before** you paste it
into ChatGPT, Claude or anything else online.

## Why this exists

OpenAI released [Privacy Filter](https://github.com/openai/privacy-filter), a small
open-weight model that labels personal information. On a Mac it has two problems:

1. **It won't run in LM Studio or other chat apps.** It's a token classifier, not a chat
   model; chat apps crash on it (`'Model' object has no attribute 'get_input_embeddings'`).
2. **The reference tool runs on the CPU** on a Mac. A ~51 KB bank statement took about
   8 minutes on an M4 MacBook Air.

And one accuracy problem: it **misses names written in ALL CAPS**, which is exactly how
bank statements print the account holder.

redact-mac fixes all three:

| | OpenAI reference (CPU) | redact-mac (MLX, GPU) |
|---|---|---|
| ~51 KB bank statement, M4 MacBook Air 16 GB | ~8 min¹ | ~20 s |
| Account holder's ALL-CAPS name left visible | 12 lines | 0 lines |
| Interface | terminal | Mac app with a Finder file picker |

¹ That CPU run overlapped with another job for part of the time; treat it as "minutes", not an exact figure.

## How it works

- **Same decoding as OpenAI's tool.** Only the model's forward pass is swapped for the
  [MLX port](https://huggingface.co/mlx-community/openai-privacy-filter-bf16) (same bf16
  weights). Tokenization, the constrained Viterbi decoder and span logic are OpenAI's
  `opf` code. On a 600-line synthetic ledger the two pipelines differed on ~10% of lines
  (bf16 rounding, mostly date boundaries) and missed a similar number of names (4 vs 3).
- **Chunked to fit in memory.** Each layer looks ±128 tokens; 8 layers → 1024 tokens of
  context per side. Long documents run in 2048-token chunks with 1024-token margins, which
  matches a single full pass.
- **ALL-CAPS fix.** Lines in capitals are title-cased before the model reads them (same
  length, so positions map back exactly); the output keeps the original text.
- **Always-redact list.** A plain text file of words that are removed every time
  (case-insensitive, whole words): your name and its variants, street, employer. A
  guaranteed backstop for what the model misses. If the list exists but can't be read,
  the app stops with an error instead of producing output without it.
- **Inputs:** .txt .md .csv .docx .doc .rtf .html .pdf (text-based PDFs; scanned pages
  have no text and are rejected). **Output:** plain text, `<name> (redacted).txt` in Downloads.

## Install

Requires an Apple-silicon Mac, [uv](https://docs.astral.sh/uv/) (`brew install uv`) and ~4 GB free.

```bash
git clone https://github.com/<you>/redact-mac && cd redact-mac
./install.sh
```

This creates:

| What | Where |
|---|---|
| App | `~/Applications/redact-mac.app`; add it to your Dock |
| Your always-redact list | `~/Applications/redact-mac — Always redact.txt` |
| Python environment | `~/.local/share/redact-mac/` |
| Model (2.8 GB) | `~/.cache/huggingface/` |
| Log (file paths and errors only, never content) | `~/Library/Logs/redact-mac.log` |

The list sits next to the app because macOS blocks apps from reading ~/Documents without
a permission grant.

Uninstall: `./uninstall.sh` (add `--all` to also delete your list).

## Use

Open the app and choose one or more files in the Finder window (it starts in Downloads;
unsupported file types are greyed out). A progress window shows; results open when done. Typically 15–30 seconds per file.

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
~/.local/share/redact-mac/venv/bin/python -m unittest discover -s tests
```

Unit tests need only the standard library; the end-to-end model test runs when the
environment and model are installed. All test data is fake.

## Status and roadmap

Early, personal tool made public. Planned:

- Own MLX implementation of the model (drop the `mlx-embeddings` dependency)
- Keep the original format (Word in → Word out)
- Optional review screen that highlights each redaction before saving

## License

GPL-3.0-or-later (see [LICENSE](LICENSE)), because the GPU path uses
[mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings) (GPL-3.0). Third-party
components and their licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Not affiliated with OpenAI.
