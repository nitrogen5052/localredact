"""Redact a text file with OpenAI Privacy Filter on the Apple GPU (MLX).

Usage: python redact.py INPUT.txt OUTPUT.txt [ALWAYS_REDACT.txt]

Only the model forward pass runs in MLX; tokenization, Viterbi decoding and span
logic are OpenAI's own `opf` code, so results match the reference pipeline
(up to bf16 rounding).
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CKPT = HERE / "opf_checkpoint"  # opf config + Viterbi calibration (no weights)
MLX_REPO = "mlx-community/openai-privacy-filter-bf16"
MLX_REVISION = "c855bd1412b817aa24a29847f7877a4389bb5ce7"

# Each layer attends +/-128 tokens; 8 layers give a 1024-token receptive field per side.
# Chunking with a 1024-token margin therefore matches one full pass, in bounded memory.
CORE, MARGIN = 2048, 1024
LIST_PLACEHOLDER = "<PRIVATE_PERSON>"


def soften_caps(text):
    """Title-case ALL-CAPS lines for the model, which misses names written in capitals.

    Only lines whose length is unchanged are converted, so character offsets still
    point into the original text.
    """
    out = []
    for line in text.splitlines(keepends=True):
        titled = line.title()
        if any(c.isalpha() for c in line) and line == line.upper() and len(titled) == len(line):
            out.append(titled)
        else:
            out.append(line)
    return "".join(out)


def read_terms(path):
    """Terms from an always-redact list: one per line, '#' starts a comment."""
    terms = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        term = raw.strip()
        if term and not term.startswith("#"):
            terms.append(term)
    return terms


def term_spans(text, terms):
    """(start, end) for each term: case-insensitive, whole words, any whitespace between words."""
    spans = []
    for term in terms:
        pattern = r"\s+".join(re.escape(w) for w in term.split())
        for m in re.finditer(rf"(?<!\w){pattern}(?!\w)", text, flags=re.IGNORECASE):
            spans.append((m.start(), m.end()))
    return spans


def apply_spans(text, spans):
    """Replace (start, end, placeholder) spans; overlapping spans merge, keeping the first placeholder."""
    spans = sorted(spans, key=lambda s: (s[0], -(s[1] - s[0])))
    merged = []
    for start, end, ph in spans:
        if merged and start < merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end, merged[-1][2])
            continue
        merged.append((start, end, ph))
    pieces, cursor = [], 0
    for start, end, ph in merged:
        pieces.append(text[cursor:start])
        pieces.append(ph)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


class _MLXModel:
    """Callable with opf's model interface (torch tokens in, torch logits out), run in MLX."""

    def __init__(self, model):
        self.model = model

    def __call__(self, tokens, attention_mask=None):
        import mlx.core as mx
        import numpy as np
        import torch

        ids = tokens[0].tolist()
        n = len(ids)
        parts = []
        for start in range(0, n, CORE):
            lo, hi = max(0, start - MARGIN), min(n, start + CORE + MARGIN)
            out = self.model(mx.array([ids[lo:hi]], dtype=mx.int32)).logits.astype(mx.float32)
            mx.eval(out)
            parts.append(torch.from_numpy(np.array(out[0, start - lo:min(n, start + CORE) - lo])))
        return torch.cat(parts, dim=0)[None]


def build_redactor():
    import tiktoken
    import torch
    from huggingface_hub import snapshot_download
    from mlx_embeddings.utils import load
    from opf._api import OPF
    from opf._common.label_space import resolve_label_space_from_config
    from opf._core.runtime import InferenceRuntime
    from opf._core.sequence_labeling import build_label_info

    config = json.loads((CKPT / "config.json").read_text())
    _, _, ner_names = resolve_label_space_from_config(config, context=str(CKPT / "config.json"))
    label_info = build_label_info(ner_names)

    model_dir = snapshot_download(MLX_REPO, revision=MLX_REVISION, local_files_only=True)
    model, _ = load(model_dir)
    id2label = {int(k): v for k, v in model.config.id2label.items()}
    if [id2label[i] for i in range(len(id2label))] != list(ner_names):
        raise SystemExit("Label order differs between the MLX model and opf; refusing to run.")

    encoding = tiktoken.get_encoding(config["encoding"])
    runtime = InferenceRuntime(
        checkpoint=str(CKPT), model=_MLXModel(model), encoding=encoding, label_info=label_info,
        device=torch.device("cpu"), n_ctx=10**9, trim_span_whitespace=True,
        discard_overlapping_predicted_spans=False, output_mode="typed",
        active_encoding_name=config["encoding"], pad_token_id=int(encoding.eot_token),
        bidirectional_context=config["bidirectional_context"], category_version="",
    )
    redactor = OPF(model=str(CKPT), device="cpu")
    redactor._runtime = runtime  # opf only supports torch devices; inject the MLX runtime
    return redactor


def redact(text, terms=()):
    from opf._core.runtime import predict_text

    redactor = build_redactor()
    runtime, decoder = redactor.get_prediction_components()
    pred = predict_text(runtime, soften_caps(text), decoder=decoder)
    base = pred.text if pred.decoded_mismatch else text
    spans = [(s.start, s.end, s.placeholder) for s in pred.spans]
    spans += [(a, b, LIST_PLACEHOLDER) for a, b in term_spans(base, terms)]
    return apply_spans(base, spans)


def main():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    src, dst = sys.argv[1], sys.argv[2]
    # A list that exists but can't be read raises here: it must fail loudly, never be skipped.
    terms = read_terms(sys.argv[3]) if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else []
    text = Path(src).read_text(encoding="utf-8")
    Path(dst).write_text(redact(text, terms), encoding="utf-8")


if __name__ == "__main__":
    main()
