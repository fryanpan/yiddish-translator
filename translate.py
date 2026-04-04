#!/usr/bin/env python3
"""
Yiddish PDF Translator

Translates a scanned Yiddish PDF book to English using Claude vision API (OCR + translation).
Processes page images using pdf2image, sends to Claude for OCR + translation in one pass.

Usage:
    python translate.py input.pdf output.md
    python translate.py input.pdf output.md --pages 45-67
"""

import sys
import os
import argparse
import base64
import io
from pathlib import Path

import anthropic
import fitz  # PyMuPDF


SYSTEM_PROMPT = """You are an expert translator specializing in Yiddish manuscripts and historical texts.
You are working on a book about Jewish life in Galicia (Eastern Europe), including towns, people, and community history.
"""

TRANSLATION_PROMPT = """This is a scanned page from a Yiddish book about Jewish life in Galicia. Please:

1. **OCR the Yiddish text**: Read the text from the image carefully. The page may have two columns — process the LEFT column first, then the RIGHT column.

2. **Join hyphenated words**: When a word is split across a line break with a hyphen, join them into one word (e.g., "Rud-\nnik" → "Rudnik").

3. **Translate to English**: Translate the full text into clear, readable English. This is for family heritage purposes — aim for generally understandable, not perfectionistic.

4. **Proper nouns**: Transliterate names of people and places into Latin letters, with the original Yiddish/Hebrew in parentheses after the first occurrence. Example: "Rudnik (רודניק)" or "Yankev Goldberg (יענקעוו גאָלדבערג)".

5. **Image captions**: If there is a caption under a photograph or illustration, prefix it with [CAPTION].

6. **Page numbers and headers**: If there is a page number or running header/footer at the top or bottom of the page, include it in brackets, e.g., [Page 47] or [Header: Chapter 3].

Output only the translated text — do not include explanations, commentary, or meta-text about your translation process.
If the page is blank or contains only decorative elements with no text, output: [Empty page]
"""


def image_to_base64(image) -> str:
    """Convert a PIL image to base64-encoded JPEG string."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def translate_page_image(client: anthropic.Anthropic, image, page_num: int) -> str:
    """Translate a single page image using Claude vision (OCR + translation in one pass)."""
    image_data = image_to_base64(image)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": TRANSLATION_PROMPT,
                        },
                    ],
                }
            ],
        )
        return message.content[0].text
    except anthropic.APIError as e:
        return f"[Translation failed: {e}]"
    except Exception as e:
        return f"[Translation failed: {e}]"


def parse_page_range(pages_arg: str, total_pages: int) -> list[int]:
    """Parse a page range string like '45-67' or '1,5,10-15' into a list of 1-based page numbers."""
    result = set()
    for part in pages_arg.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start.strip()))
            end = min(total_pages, int(end.strip()))
            result.update(range(start, end + 1))
        else:
            n = int(part)
            if 1 <= n <= total_pages:
                result.add(n)
    return sorted(result)


def translate_pdf(input_path: str, output_path: str, pages_arg: str | None = None, dpi: int = 200) -> None:
    """Main translation function: convert PDF pages to images and translate each one."""
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    if not input_path.lower().endswith(".pdf"):
        print("Error: Input file must be a PDF.", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY environment variable not set.\n"
            "Get your key at https://console.anthropic.com and run:\n"
            "  export ANTHROPIC_API_KEY=your_key_here",
            file=sys.stderr,
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    pdf_name = Path(input_path).name

    doc = fitz.open(input_path)
    total_pages = len(doc)
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    def render_page(page_num: int):
        """Render a 1-based page number to a PIL Image."""
        from PIL import Image as PILImage
        pix = doc[page_num - 1].get_pixmap(matrix=mat)
        return PILImage.open(io.BytesIO(pix.tobytes("jpeg")))

    # Determine page range
    if pages_arg:
        pages_to_process = parse_page_range(pages_arg, total_pages)
        print(f"Processing pages: {pages_to_process}")
    else:
        pages_to_process = list(range(1, total_pages + 1))
        print(f"Found {total_pages} pages.")

    images = [render_page(p) for p in pages_to_process]

    # Load existing output if doing partial re-run (pages_arg set)
    existing_content = {}
    if pages_arg and os.path.exists(output_path):
        # Parse existing markdown to preserve pages we're not re-running
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Split by page markers
        import re
        sections = re.split(r"\n## Page (\d+)\n", content)
        if len(sections) > 1:
            # sections[0] is header, then alternating: page_num, content
            for i in range(1, len(sections), 2):
                if i + 1 < len(sections):
                    existing_content[int(sections[i])] = sections[i + 1].rstrip("\n-").strip()

    # Translate pages
    translations = {}
    for i, (page_num, image) in enumerate(zip(pages_to_process, images)):
        print(f"Translating page {page_num} ({i + 1}/{len(pages_to_process)})...", end=" ", flush=True)
        translated = translate_page_image(client, image, page_num)
        translations[page_num] = translated
        print("done")

    # Merge with existing content
    all_page_nums = sorted(set(list(existing_content.keys()) + list(translations.keys())))

    # Write output
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    lines = [f"# Translation of: {pdf_name}", "", "---", ""]
    for page_num in all_page_nums:
        text = translations.get(page_num) or existing_content.get(page_num, "[Not translated]")
        lines.extend([
            f"## Page {page_num}",
            "",
            text,
            "",
            "---",
            "",
        ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nTranslation complete! Output saved to: {output_path}")
    if pages_arg:
        print(f"Re-ran pages: {pages_to_process}")


def main():
    parser = argparse.ArgumentParser(
        description="Translate a scanned Yiddish PDF book to English using Claude vision",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python translate.py nybc314143.pdf translation.md
  python translate.py nybc314143.pdf translation.md --pages 45-67
  python translate.py nybc314143.pdf translation.md --pages 1,5,10-15 --dpi 300

Environment variables:
  ANTHROPIC_API_KEY  Your Anthropic API key (required)
        """,
    )
    parser.add_argument("input", help="Path to the input PDF file (scanned)")
    parser.add_argument("output", help="Path for the output Markdown file")
    parser.add_argument(
        "--pages",
        help="Page range to process, e.g. '45-67' or '1,5,10-15'. "
             "When set with an existing output file, preserves other pages.",
        default=None,
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Resolution for PDF-to-image conversion (default: 200). Use 300+ for higher quality.",
    )

    args = parser.parse_args()
    translate_pdf(args.input, args.output, pages_arg=args.pages, dpi=args.dpi)


if __name__ == "__main__":
    main()
