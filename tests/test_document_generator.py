import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


class FakeFont:
    def __init__(self) -> None:
        self.name = None
        self.size = None


class FakeRun:
    def __init__(self) -> None:
        self.font = FakeFont()


class FakeParagraph:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.runs = [FakeRun()] if text else []
        self.alignment = None

    def add_run(self) -> FakeRun:
        run = FakeRun()
        self.runs.append(run)
        return run


class FakeSection:
    def __init__(self) -> None:
        self.top_margin = None
        self.bottom_margin = None
        self.left_margin = None
        self.right_margin = None


class FakeDocument:
    last_created = None

    def __init__(self) -> None:
        self.sections = [FakeSection()]
        self.paragraphs = []
        self.saved_path = None
        FakeDocument.last_created = self

    def add_heading(self, text: str, level: int = 1) -> FakeParagraph:
        paragraph = FakeParagraph(text)
        self.paragraphs.append(paragraph)
        return paragraph

    def add_paragraph(self, text: str = "") -> FakeParagraph:
        paragraph = FakeParagraph(text)
        self.paragraphs.append(paragraph)
        return paragraph

    def save(self, path: str) -> None:
        self.saved_path = path


fake_docx = types.ModuleType("docx")
fake_docx.Document = FakeDocument
sys.modules.setdefault("docx", fake_docx)

fake_enum_text = types.ModuleType("docx.enum.text")
fake_enum_text.WD_ALIGN_PARAGRAPH = types.SimpleNamespace(CENTER="CENTER")
sys.modules.setdefault("docx.enum.text", fake_enum_text)

fake_shared = types.ModuleType("docx.shared")
fake_shared.Inches = lambda value: value
fake_shared.Pt = lambda value: value
sys.modules.setdefault("docx.shared", fake_shared)

document_generator = importlib.import_module("services.document_generator")
build_output_paths = document_generator.build_output_paths
save_docx = document_generator.save_docx
save_markdown = document_generator.save_markdown


class DocumentGeneratorTests(unittest.TestCase):
    def test_build_output_paths_sanitizes_company_name_and_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            paths = build_output_paths(output_dir, "Acme/Corp: Ltd", "JOB-123")

            expected_dir = output_dir / "Acme_Corp__Ltd"
            self.assertEqual(paths["email_md"], expected_dir / "Acme_Corp__Ltd_JOB-123_recruiter_email.md")
            self.assertEqual(paths["email_docx"], expected_dir / "Acme_Corp__Ltd_JOB-123_recruiter_email.docx")
            self.assertEqual(paths["cover_letter_md"], expected_dir / "Acme_Corp__Ltd_JOB-123_cover_letter.md")
            self.assertEqual(paths["cover_letter_docx"], expected_dir / "Acme_Corp__Ltd_JOB-123_cover_letter.docx")
            self.assertTrue(expected_dir.exists())

    def test_save_markdown_writes_utf8_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "email.md"
            content = "# Hello\n\nThis is test."

            save_markdown(content, file_path)

            self.assertEqual(file_path.read_text(encoding="utf-8"), content)

    def test_save_docx_writes_title_and_body_paragraphs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "cover_letter.docx"

            save_docx("Line one\nLine two", file_path, title="Cover Letter")

            document = FakeDocument.last_created
            paragraphs = [paragraph.text for paragraph in document.paragraphs]

            self.assertEqual(paragraphs[0], "Cover Letter")
            self.assertEqual(paragraphs[2:], ["Line one", "Line two"])
            self.assertEqual(document.saved_path, str(file_path))
            self.assertEqual(document.paragraphs[0].alignment, "CENTER")
            self.assertEqual(document.paragraphs[2].runs[0].font.name, "Calibri")
            self.assertEqual(document.paragraphs[2].runs[0].font.size, 11)


if __name__ == "__main__":
    unittest.main()
