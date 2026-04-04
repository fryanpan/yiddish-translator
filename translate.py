#!/usr/bin/env python3
"""
Yiddish PDF Translator

Translates a Yiddish PDF book to English using Claude AI, page by page.

Usage:
    python translate.py input.pdf output.md
"""

import sys
import os
import argparse
from pathlib import Path

import fitz  # PyMuPDF
import anthropic


def extract_pages(pdf_path: str) -> list[str]:
    """Extract text from each page of a PDF."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages.append(text)
    doc.close()
    return pages


def translate_page(client: anthropic.Anthropic, page_text: str, page_num: int) -> str:
    """Translate a single page from Yiddish to English using Claude."""
    if not page_text.strip():
        return "[Empty page]"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": (
                    "Please translate the following text from Yiddish to English. "
                    "Preserve the paragraph structure and formatting as much as possible. "
                    "If any words are unclear or ambiguous, provide the most likely translation "
                    "and note any significant uncertainties in brackets.\n\n"
                    f"Text to translate:\n\n{page_text}"
                ),
            }
        ],
    )

    return message.content[0].text


def translate_pdf(input_path: str, output_path: str) -> None:
    """Main translation function: extract PDF pages and translate each one."""
    # Validate input file
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    if not input_path.lower().endswith(".pdf"):
        print("Error: Input file must be a PDF.", file=sys.stderr)
        sys.exit(1)

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY environment variable not set.\n"
            "Get your key at https://console.anthropic.com and run:\n"
            "  export ANTHROPIC_API_KEY=your_key_here",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Extracting pages from {input_path}...")
    pages = extract_pages(input_path)
    total_pages = len(pages)
    print(f"Found {total_pages} pages.")

    client = anthropic.Anthropic(api_key=api_key)

    pdf_name = Path(input_path).name
    output_lines = [f"# Translation of: {pdf_name}", "", "---", ""]

    for i, page_text in enumerate(pages, start=1):
        print(f"Translating page {i}/{total_pages}...", end=" ", flush=True)

        try:
            translated = translate_page(client, page_text, i)
            print("done")
        except anthropic.APIError as e:
            print(f"API error: {e}")
            translated = f"[Translation failed: {e}]"
        except Exception as e:
            print(f"error: {e}")
            translated = f"[Translation failed: {e}]"

        output_lines.extend([
            f"## Page {i}",
            "",
            translated,
            "",
            "---",
            "",
        ])

    output_content = "\n".join(output_lines)

    # Write output
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"\nTranslation complete! Output saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Translate a Yiddish PDF book to English using Claude AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python translate.py mybook.pdf translation.md
  python translate.py /path/to/book.pdf /path/to/output.md

Environment variables:
  ANTHROPIC_API_KEY  Your Anthropic API key (required)
        """,
    )
    parser.add_argument("input", help="Path to the input PDF file")
    parser.add_argument("output", help="Path for the output Markdown file")

    args = parser.parse_args()
    translate_pdf(args.input, args.output)


if __name__ == "__main__":
    main()
