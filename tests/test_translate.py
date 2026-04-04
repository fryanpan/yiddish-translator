"""Tests for the Yiddish translator (vision-based OCR + translation)."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from PIL import Image

# Add parent dir to path so we can import translate
sys.path.insert(0, str(Path(__file__).parent.parent))

from translate import translate_page_image, parse_page_range, translate_pdf


class TestParsePageRange:
    def test_simple_range(self):
        assert parse_page_range("1-3", 10) == [1, 2, 3]

    def test_single_page(self):
        assert parse_page_range("5", 10) == [5]

    def test_comma_separated(self):
        assert parse_page_range("1,5,10", 10) == [1, 5, 10]

    def test_mixed(self):
        assert parse_page_range("1,5-7,10", 15) == [1, 5, 6, 7, 10]

    def test_clamps_to_total_pages(self):
        assert parse_page_range("8-15", 10) == [8, 9, 10]

    def test_deduplicates(self):
        assert parse_page_range("1-3,2-4", 10) == [1, 2, 3, 4]


class TestTranslatePageImage:
    def test_calls_claude_with_image(self):
        """translate_page_image sends the image to Claude and returns response text."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello world")]
        mock_client.messages.create.return_value = mock_response

        # Create a small dummy PIL image
        image = Image.new("RGB", (100, 100), color="white")

        result = translate_page_image(mock_client, image, 1)

        assert result == "Hello world"
        mock_client.messages.create.assert_called_once()

        # Verify correct model and vision content
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        content = messages[0]["content"]
        # Should have image block and text block
        types = [c["type"] for c in content]
        assert "image" in types
        assert "text" in types

    def test_api_error_returns_placeholder(self):
        """translate_page_image returns error placeholder on API failure."""
        import anthropic as anthropic_mod

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic_mod.APIError(
            message="Rate limit", request=MagicMock(), body={}
        )

        image = Image.new("RGB", (100, 100), color="white")
        result = translate_page_image(mock_client, image, 1)

        assert result.startswith("[Translation failed:")


class TestTranslatePdf:
    def test_missing_input_file_exits(self):
        with pytest.raises(SystemExit):
            translate_pdf("nonexistent.pdf", "output.md")

    def test_non_pdf_input_exits(self, tmp_path):
        txt_file = tmp_path / "book.txt"
        txt_file.write_text("some text")
        with pytest.raises(SystemExit):
            translate_pdf(str(txt_file), "output.md")

    def test_missing_api_key_exits(self, tmp_path):
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit):
                translate_pdf(str(pdf_file), "output.md")

    def test_full_translation_flow(self, tmp_path):
        """translate_pdf converts images and translates each page."""
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")
        output_file = tmp_path / "output.md"

        mock_images = [Image.new("RGB", (100, 100)), Image.new("RGB", (100, 100))]
        mock_translations = ["Hello world", "Good morning"]

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("translate.convert_from_path", return_value=mock_images):
                with patch("translate.translate_page_image", side_effect=mock_translations):
                    with patch("anthropic.Anthropic"):
                        translate_pdf(str(pdf_file), str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "## Page 1" in content
        assert "Hello world" in content
        assert "## Page 2" in content
        assert "Good morning" in content
        assert "# Translation of: book.pdf" in content

    def test_creates_output_directory(self, tmp_path):
        pdf_file = tmp_path / "book.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")
        output_file = tmp_path / "subdir" / "output.md"

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("translate.convert_from_path", return_value=[Image.new("RGB", (100, 100))]):
                with patch("translate.translate_page_image", return_value="translation"):
                    with patch("anthropic.Anthropic"):
                        translate_pdf(str(pdf_file), str(output_file))

        assert output_file.exists()
