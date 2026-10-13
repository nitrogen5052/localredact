"""Platform-independent localredact logic, shared by the Mac and Windows apps.

The model runtime (MLX on Mac, PyTorch on Windows) is built by each platform; this
module runs it with OpenAI's `opf` decoding and applies localredact's fixes:
the ALL-CAPS name fix and the always-redact list.
"""
import re
from pathlib import Path

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
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
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


def redact_with(redactor, text, terms=()):
    """Redact `text` with an `opf.OPF` redactor, plus the caps fix and the always-redact list."""
    from opf._core.runtime import predict_text

    runtime, decoder = redactor.get_prediction_components()
    pred = predict_text(runtime, soften_caps(text), decoder=decoder)
    base = pred.text if pred.decoded_mismatch else text
    spans = [(s.start, s.end, s.placeholder) for s in pred.spans]
    spans += [(a, b, LIST_PLACEHOLDER) for a, b in term_spans(base, terms)]
    return apply_spans(base, spans)
