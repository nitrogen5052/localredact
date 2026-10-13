"""Tests for the shared core, plus the Mac engine end to end when MLX and its model are installed.
Unit tests need only the standard library: python -m unittest discover -s tests"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "core"), str(ROOT / "mac")]
import redact_core as redact  # noqa: E402

FAKE = "Hi, I am Jane Testperson. Email jane.test@example.com or call 555-123-4567.\n"


class SoftenCaps(unittest.TestCase):
    def test_all_caps_line_is_title_cased_same_length(self):
        text = "PAYMENT FROM JOHN QWERTYSON - INDIVIDUAL\nnormal line\n"
        out = redact.soften_caps(text)
        self.assertEqual(out, "Payment From John Qwertyson - Individual\nnormal line\n")
        self.assertEqual(len(out), len(text))

    def test_mixed_case_and_numeric_lines_unchanged(self):
        text = "Balance $1,204.55\n12/31/2026\nAcct 4242\n"
        self.assertEqual(redact.soften_caps(text), text)


class Terms(unittest.TestCase):
    def test_case_insensitive_whole_word_any_spacing(self):
        text = "Statement for JOHN  QWERTYSON\nqwertyson Bros; Qwertysons excluded"
        spans = redact.term_spans(text, ["John Qwertyson", "Qwertyson"])
        found = sorted(text[a:b] for a, b in spans)
        self.assertEqual(found, ["JOHN  QWERTYSON", "QWERTYSON", "qwertyson"])

    def test_read_terms_skips_comments_and_blanks(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("# comment\n\n  Jane Doe  \nAcme\n")
        self.assertEqual(redact.read_terms(f.name), ["Jane Doe", "Acme"])

    def test_unreadable_list_raises(self):
        with self.assertRaises(OSError):
            redact.read_terms("/nonexistent/dir/list.txt")


class ApplySpans(unittest.TestCase):
    def test_overlaps_merge_to_widest(self):
        text = "Pay John Qwertyson now"
        spans = [(4, 8, "<A>"), (4, 18, "<B>"), (9, 18, "<C>")]
        self.assertEqual(redact.apply_spans(text, spans), "Pay <B> now")

    def test_no_spans(self):
        self.assertEqual(redact.apply_spans("abc", []), "abc")


def _mlx_model_available():
    if importlib.util.find_spec("mlx_embeddings") is None:
        return False
    try:
        import engine_mlx
        from huggingface_hub import snapshot_download
        snapshot_download(engine_mlx.MLX_REPO, revision=engine_mlx.MLX_REVISION, local_files_only=True)
        return True
    except Exception:
        return False


@unittest.skipUnless(_mlx_model_available(), "Mac MLX environment and model required")
class MacModel(unittest.TestCase):
    def test_fake_record_is_redacted(self):
        import engine_mlx
        out = engine_mlx.redact(FAKE + "STATEMENT FOR JOHN QWERTYSON\n", ["Testperson"])
        for leaked in ("Jane", "Testperson", "jane.test@example.com", "555-123-4567", "QWERTYSON"):
            self.assertNotIn(leaked, out)
        self.assertIn("<PRIVATE_EMAIL>", out)


if __name__ == "__main__":
    unittest.main()
