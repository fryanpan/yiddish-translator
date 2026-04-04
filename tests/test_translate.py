"""Tests for the Yiddish translator."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

# Add parent dir to path so we can import translate
sys.path.insert(0, str(Path(__file__).parent.parent))

from translate import extract_pages, translate_page, translate_pdf


class TestExtractPages:
    def test_returns_list_of_strings(self):
        """extract_pages returns a list of strings, one per page."""
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "שלום וועלט"
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "גוט מאָרגן"
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_doc.__getitem__ = MagicMock(side_effect=[mock_page1, mock_page2])

        with patch("fitz.open", return_value=mock_doc):
            result = extract_pages("dummy.pdf")

        assert result == ["שלום וועלט", "גוט מאָרגן"]
        mock_doc.close.assert_called_once()

    def test_empty_pdf(self):
        """extract_pages handles a PDF with no pages."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_doc.__getitem__ = MagicMock(side_effect=IndexError)

        with patch("fitz.open", return_value=mock_doc):
            result = extract_pages("empty.pdf")

        assert result == []


class TestTranslatePage:
    def test_translates_non_empty_page(self):
        """translate_page calls Claude and returns translated text."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello world")]
        mock_client.messages.create.return_value = mock_response

        result = translate_page(mock_client, "שלום וועלט", 1)

        assert result == "Hello world"
        mock_client.messages.create.assert_called_once()

        # Verify the call used the right model
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-sonnet-4-6"

    def test_empty_page_returns_placeholder(self):
        """translate_page returns a placeholder for empty pages."""
        mock_client = MagicMock()
        result = translate_page(mock_client, "   \n  ", 1)
        assert result == "[Empty page]"
        mock_client.messages.create.assert_not_called()

    def test_whitespace_only_page(self):
        """translate_page treats whitespace-only pages as empty."""
        mock_client = MagicMock()
        result = translate_page(mock_client, "\t\n\r  ", 2)
        assert result == "[Empty page]"


class TestTranslatePdf:
    def test_missing_input_file_exits(self):
        """translate_pdf exits with error if input file doesn't exist."""
        with pytest.raises(SystemExit):
            translate_pdf("nonexistent.pdf", "output.md")

    def test_non_pdf_input_exits(self, tmp_path):
        """translate_pdf exits with error if input is not a PDF."""
        txt_file = tmp_path / "book.txt"
        txt_file.write_text("some text")
        with pytest.raises(SystemExit):
            translate_pdf(str(txt_file), "output.md")

    def test_missing_api_key_exits(self, tmp_path):
        """translate_pdf exits with error if ANTHROPIC_API_KEY is not set."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit):
                translate_pdf(str(pdf_file), "output.md")

    def test_full_translation_flow(self, tmp_path):
        """translate_pdf orchestrates extraction and translation correctly."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")
        output_file = tmp_path / "output.md"

        mock_pages = ["שלום וועלט", "גוט מאָרגן"]
        mock_translations = ["Hello world", "Good morning"]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("translate.extract_pages", return_value=mock_pages):
                with patch("translate.translate_page", side_effect=mock_translations):
                    with patch("anthropic.Anthropic"):
                        translate_pdf(str(pdf_file), str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "## Page 1" in content
        assert "Hello world" in content
        assert "## Page 2" in content
        assert "Good morning" in content
        assert f"# Translation of: book.pdf" in content

    def test_creates_output_directory(self, tmp_path):
        """translate_pdf creates the output directory if it doesn't exist."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")
        output_file = tmp_path / "subdir" / "output.md"

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("translate.extract_pages", return_value=["text"]):
                with patch("translate.translate_page", return_value="translation"):
                    with patch("anthropic.Anthropic"):
                        translate_pdf(str(pdf_file), str(output_file))

        assert output_file.exists()
