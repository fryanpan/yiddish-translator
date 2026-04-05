#!/usr/bin/env python3
"""
Yiddish PDF OCR Tool

Extracts cleaned Yiddish text from a scanned PDF book using a two-pass Claude vision approach:
  Pass 1: Raw OCR — read the Hebrew-script Yiddish text from the page image
  Pass 2: Disambiguation — correct commonly confused letters using context and linguistic rules

Processes page images using PyMuPDF, sends to Claude for OCR in one pass then cleanup in a second.

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


SYSTEM_PROMPT = """You are an expert in Yiddish manuscripts and historical texts, with deep knowledge of \
YIVO-standard Yiddish orthography and early 20th-century Ashkenazi typography. \
You are working on a book about Jewish life in Galicia (Eastern Europe), including towns, people, and community history.
"""

YIDDISH_OCR_PROMPT = """This is a scanned page from a Yiddish book (early-to-mid 20th century Ashkenazi print) \
about Jewish life in Galicia. Please OCR the Yiddish text from this image.

Instructions:
1. Output ONLY the original Yiddish text in Hebrew script — do NOT translate to English.
2. The page may have two columns — process the LEFT column first, then the RIGHT column.
3. Read each line carefully, including headers, captions, and page numbers.
4. If there is a caption under a photograph or illustration, prefix it with [CAPTION].
5. If there is a page number or running header/footer, include it in brackets, e.g., [דף 47] or keep the numeral.
6. Preserve line breaks as they appear on the page — use a single newline for each line break.
7. Use a blank line to indicate a clear visual paragraph or section break.
8. If the page is blank or contains only decorative elements, output: [דף פּוסט]

Output only the Yiddish text — no explanations, no English, no commentary.
"""

YIDDISH_DISAMBIGUATION_PROMPT = """You are given raw OCR output of a page from an early 20th-century Yiddish book \
(Ashkenazi typography). Old Yiddish print has characteristic OCR errors. Your task is to:

1. **Fix commonly confused letter pairs** using context, word meaning, and YIVO orthographic rules:

   - **ר (resh) vs ד (daled)**: Resh is 3–5× more common in Yiddish than daled. In old print, \
the top-right curve of resh can look like the boxy head of daled. Use word context to decide. \
Example: the surname suffix -רייך (Reich) is correct; -דייך (Deikh) is not a Yiddish surname. \
The author's name is אסתר קאַלער-רייך — if you see קאַלער-דייך, correct to קאַלער-רייך.

   - **ם (mem-sofit) vs ס (samech)**: Mem-sofit (ם) is square-bottomed and appears ONLY at the end \
of a word. Samech (ס) is rounded and appears only mid-word or word-initial — never word-final. \
If you see ס at word-end, it should almost certainly be ם.

   - **ו (vav) vs ז (zayin)**: Zayin has a horizontal bar/crown at the top; vav is a plain vertical \
stroke. Use word context to resolve ambiguity.

   - **ה (he) vs ח (khet) vs ת (tav)**: He is open top-left; khet is closed/rounded; tav is square \
with a closed top. He appears as a common suffix (feminine nouns, definite article); khet and tav \
appear in Hebraic/Aramaic vocabulary.

   - **Final forms**: The five letters מ נ כ פ צ must use their sofit forms (ם ן ך ף ץ) at \
word-end. Correct any that are missing their sofit form.

2. **Normalize line breaks**:
   - Hyphenated line-breaks: when a word is split with a hyphen at a line end (e.g., "ייִד-\nיש"), \
rejoin into one word ("ייִדיש") and remove the hyphen.
   - Soft line-wraps: a line break within a paragraph (not preceded by a hyphen) is usually just \
word-wrap from the column layout. Join those lines into flowing text, separated by a space.
   - Real paragraph breaks: a blank line in the OCR output, or a clear section/chapter break, \
should remain as a blank line in the output.

3. **Do not translate** — output only corrected Yiddish text in Hebrew script.

4. **Preserve** headers, captions (marked [CAPTION]), page numbers, and section dividers.

Here is the raw OCR output to clean up. Preserve ALL text — both columns if the page has two columns:

<ocr_text>
{ocr_text}
</ocr_text>

Output the corrected Yiddish text only, with no English, no commentary, and no explanations. \
Do not omit any content that was in the OCR output.
"""


def image_to_base64(image) -> str:
    """Convert a PIL image to base64-encoded JPEG string."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def translate_page_image(client: anthropic.Anthropic, image, page_num: int) -> str:
    """OCR a single page image using two-pass Claude vision: raw OCR then letter disambiguation."""
    image_data = image_to_base64(image)

    try:
        # Pass 1: raw OCR — extract Yiddish text from image
        pass1 = client.messages.create(
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
                            "text": YIDDISH_OCR_PROMPT,
                        },
                    ],
                }
            ],
        )
        raw_ocr = pass1.content[0].text

        # Pass 2: disambiguation — fix confused letters and normalize newlines
        pass2 = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": YIDDISH_DISAMBIGUATION_PROMPT.format(ocr_text=raw_ocr),
                }
            ],
        )
        return pass2.content[0].text

    except anthropic.APIError as e:
        return f"[OCR failed: {e}]"
    except Exception as e:
        return f"[OCR failed: {e}]"


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
    """Main OCR function: convert PDF pages to images and extract cleaned Yiddish text from each."""
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

    # OCR pages (two-pass per page)
    translations = {}
    for i, (page_num, image) in enumerate(zip(pages_to_process, images)):
        print(f"OCR page {page_num} ({i + 1}/{len(pages_to_process)})...", end=" ", flush=True)
        cleaned = translate_page_image(client, image, page_num)
        translations[page_num] = cleaned
        print("done")

    # Merge with existing content
    all_page_nums = sorted(set(list(existing_content.keys()) + list(translations.keys())))

    # Write output
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    lines = [f"# OCR of: {pdf_name}", "", "---", ""]
    for page_num in all_page_nums:
        text = translations.get(page_num) or existing_content.get(page_num, "[Not processed]")
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

    print(f"\nOCR complete! Output saved to: {output_path}")
    if pages_arg:
        print(f"Re-ran pages: {pages_to_process}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract cleaned Yiddish text from a scanned PDF using two-pass Claude vision OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python translate.py nybc314143.pdf docs/translations/all.md
  python translate.py nybc314143.pdf docs/translations/all.md --pages 45-67
  python translate.py nybc314143.pdf docs/translations/all.md --pages 1,5,10-15 --dpi 300

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
