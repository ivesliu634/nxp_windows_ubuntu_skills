from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import imx_rm as rm


def make_pdf(path: Path, *, bookmarks: bool = True, empty: bool = False) -> None:
    streams = []
    for text in ["Alpha CLOCK literal [x]", "Beta clock", "Gamma pin"]:
        content = f"BT /F1 12 Tf 72 720 Td ({'' if empty else text}) Tj ET".encode("ascii")
        streams.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
    outline = "/Outlines 3 0 R" if bookmarks else ""
    objects = [
        f"<< /Type /Catalog /Pages 2 0 R {outline} /PageLabels 14 0 R >>".encode(),
        b"<< /Type /Pages /Kids [4 0 R 5 0 R 6 0 R] /Count 3 >>",
        b"<< /Type /Outlines /First 7 0 R /Last 9 0 R /Count 3 >>",
    ]
    for number in range(3):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 10 0 R >> >> /Contents {11 + number} 0 R >>".encode()
        )
    objects.extend([
        b"<< /Title (1 Clock) /Parent 3 0 R /Dest [4 0 R /Fit] "
        b"/First 8 0 R /Last 8 0 R /Count 1 /Next 9 0 R >>",
        b"<< /Title (1.1 PLL) /Parent 7 0 R /Dest [5 0 R /Fit] >>",
        b"<< /Title (2 Pin multiplexing) /Parent 3 0 R /Dest [6 0 R /Fit] /Prev 7 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        *streams,
        b"<< /Nums [0 << /S /r >> 1 << /S /D /St 10 >>] >>",
    ])
    data = bytearray(b"%PDF-1.7\n")
    offsets = []
    for number, content in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + content + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class RMTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pdf = self.root / "imx99" / "RM" / "manual with spaces.pdf"
        make_pdf(self.pdf)

    def invoke(self, *argv: str) -> tuple[int, str, str]:
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = rm.main(list(argv))
        return code, output.getvalue(), error.getvalue()

    def test_catalog_rejects_ambiguous_chip_but_accepts_explicit_path(self) -> None:
        make_pdf(self.pdf.with_name("another revision.pdf"))
        with self.assertRaisesRegex(rm.RMError, "Ambiguous"):
            rm.resolve_pdf("imx99", self.root)
        self.assertEqual(rm.resolve_pdf(str(self.pdf), self.root), self.pdf.resolve())
        self.assertEqual(len(rm.catalog(self.root)), 2)

    def test_bookmark_ranges_include_shared_boundary_and_keep_hierarchy(self) -> None:
        index, hit = rm.ensure_index(self.pdf)
        self.assertFalse(hit)
        sections = {row["id"]: row for row in index["sections"]}
        self.assertEqual((sections["1"]["page_start"], sections["1"]["page_end"]), (1, 3))
        self.assertEqual((sections["1.1"]["page_start"], sections["1.1"]["page_end"]), (2, 3))
        self.assertEqual(sections["1.1"]["path"], "1 Clock > 1.1 PLL")
        selected, _ = rm.lookup(index, "clk", 1)
        self.assertEqual(selected[0]["id"], "1")

    def test_json_excerpt_distinguishes_pdf_page_from_label_and_attributes_source(self) -> None:
        code, output, error = self.invoke("extract", str(self.pdf), "--pages", "2", "--json")
        self.assertEqual((code, error), (0, ""))
        result = json.loads(output)
        self.assertEqual(result["pdf_path"], str(self.pdf.resolve()))
        self.assertEqual(result["sha256"], hashlib.sha256(self.pdf.read_bytes()).hexdigest())
        self.assertEqual(result["pages"][0]["pdf_page"], 2)
        self.assertEqual(result["pages"][0]["page_label"], "10")
        self.assertIn("Beta clock", result["pages"][0]["text"])
        self.assertNotIn("Gamma", result["pages"][0]["text"])

    def test_bounded_search_is_literal_and_case_insensitive(self) -> None:
        code, output, _ = self.invoke(
            "search", str(self.pdf), "CLOCK", "--pages", "2", "--json",
        )
        self.assertEqual(code, 0)
        result = json.loads(output)
        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(result["matches"][0]["pdf_page"], 2)
        code, output, _ = self.invoke(
            "search", str(self.pdf), "[x]", "--pages", "1:2", "--json",
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["total_matches"], 1)

    def test_lookup_prioritizes_owner_and_rejects_other_peripheral_instances(self) -> None:
        titles = [
            ("1", "1 Timer/PWM Module (TPM)"),
            ("register-3", "TPM3 EXT_CLK SELECT INPUT"),
            ("register-6", "TPM6 EXT_CLK SELECT INPUT"),
            ("2", "2 External Clock"),
        ]
        index = {"sections": [
            {"id": key, "title": title, "path": title, "level": 0, "page_start": number}
            for number, (key, title) in enumerate(titles, 1)
        ]}
        matches, _ = rm.lookup(index, "tpm3 ext_clk", 8)
        self.assertEqual(matches[0]["id"], "1")
        self.assertEqual(matches[0]["matched_by"], "owner-chapter")
        self.assertIn("register-3", [row["id"] for row in matches])
        self.assertNotIn("register-6", [row["id"] for row in matches])

    def test_cached_lookup_and_excerpt_do_not_reopen_the_pdf_backend(self) -> None:
        index, _ = rm.ensure_index(self.pdf)
        first = rm.read_pages(self.pdf, index, 2, 2)
        with mock.patch.object(rm.pdfium, "PdfDocument", side_effect=AssertionError("cache missed")):
            cached, hit = rm.ensure_index(self.pdf)
            self.assertTrue(hit)
            self.assertEqual(rm.read_pages(self.pdf, cached, 2, 2), first)

    def test_same_size_and_timestamp_pdf_change_invalidates_index_and_page_text(self) -> None:
        index, _ = rm.ensure_index(self.pdf)
        rm.read_pages(self.pdf, index, 1, 1)
        curated = rm.sidecar(self.pdf) / "CONTENTS.md"
        curated.write_text("manual notes", encoding="utf-8")
        stamp = self.pdf.stat()
        self.pdf.write_bytes(self.pdf.read_bytes().replace(b"Alpha CLOCK", b"Omega CLOCK"))
        os.utime(self.pdf, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        changed, hit = rm.ensure_index(self.pdf)
        self.assertFalse(hit)
        self.assertNotEqual(changed["sha256"], index["sha256"])
        self.assertIn("Omega CLOCK", rm.read_pages(self.pdf, changed, 1, 1)[0]["text"])
        self.assertEqual(curated.read_text(encoding="utf-8"), "manual notes")

    def test_schema_change_invalidates_both_index_and_page_cache(self) -> None:
        index, _ = rm.ensure_index(self.pdf)
        rm.read_pages(self.pdf, index, 1, 1)
        path = rm.sidecar(self.pdf) / "pages" / "00001.json"
        cached = json.loads(path.read_text(encoding="utf-8"))
        cached["text"] = "output from the previous extraction schema"
        path.write_text(json.dumps(cached), encoding="utf-8")
        with mock.patch.object(rm, "SCHEMA_VERSION", rm.SCHEMA_VERSION + 1):
            rebuilt, hit = rm.ensure_index(self.pdf)
            self.assertFalse(hit)
            text = rm.read_pages(self.pdf, rebuilt, 1, 1)[0]["text"]
            self.assertIn("Alpha CLOCK", text)
            self.assertNotIn("previous extraction", text)

    def test_invalid_or_over_limit_ranges_fail_explicitly(self) -> None:
        index, _ = rm.ensure_index(self.pdf)
        for value in ["0", "3:2", "1:4", "1-2"]:
            with self.subTest(pages=value), self.assertRaises(rm.RMError):
                rm.select_pages(index, None, value, 0, 20)
        with self.assertRaisesRegex(rm.RMError, "spans 3 pages"):
            rm.select_pages(index, None, "2", 1, 2)
        self.assertEqual(rm.select_pages(index, None, "2", 1, 3), (1, 3))
        with self.assertRaisesRegex(rm.RMError, "exactly one"):
            rm.select_pages(index, "1", "1", 0, 20)

    def test_no_bookmarks_still_allows_explicit_pages_but_no_false_section_lookup(self) -> None:
        make_pdf(self.pdf, bookmarks=False)
        code, output, _ = self.invoke("extract", str(self.pdf), "--pages", "1", "--json")
        self.assertEqual(code, 0)
        self.assertIn("Alpha", json.loads(output)["pages"][0]["text"])
        code, _, error = self.invoke("lookup", str(self.pdf), "clock", "--json")
        self.assertEqual(code, 1)
        self.assertIn("No matching bookmark", error)

    def test_missing_text_layer_is_not_reported_as_success(self) -> None:
        make_pdf(self.pdf, empty=True)
        code, output, error = self.invoke("extract", str(self.pdf), "--pages", "1", "--json")
        self.assertEqual((code, output), (1, ""))
        self.assertIn("no text layer", error)

    def test_corrupt_index_fails_explicitly_and_force_build_recovers(self) -> None:
        rm.ensure_index(self.pdf)
        path = rm.sidecar(self.pdf) / "index.json"
        path.write_text("{", encoding="utf-8")
        code, output, error = self.invoke("lookup", str(self.pdf), "clock", "--json")
        self.assertEqual((code, output), (1, ""))
        self.assertIn("Invalid generated cache", error)
        code, _, error = self.invoke("build", str(self.pdf), "--force", "--json")
        self.assertEqual((code, error), (0, ""))


if __name__ == "__main__":
    unittest.main()
