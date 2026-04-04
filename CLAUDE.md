# Project: yiddish-translator

## Overview
A CLI Python tool that translates a scanned Yiddish book (PDF) into English using Claude vision API.
Converts each PDF page to an image, then uses OCR + translation in a single Claude call per page.
Designed for personal family heritage use — speed and readability over perfection.

**Book:** nybc314143.pdf — a book about Jewish life in Galicia
**Source:** https://archive.org/download/nybc314143/nybc314143.pdf

## Architecture

### Development
```bash
# Install dependencies (requires poppler for pdf2image)
# macOS: brew install poppler
# Ubuntu: apt-get install poppler-utils
pip install -r requirements.txt

# Run full translation
python translate.py nybc314143.pdf translation.md

# Re-run specific pages (e.g. for higher quality)
python translate.py nybc314143.pdf translation.md --pages 45-67
python translate.py nybc314143.pdf translation.md --pages 1,5,10-15 --dpi 300

# Run tests
python -m pytest tests/
```

### Key Files

| File | Purpose |
|------|---------|
| `translate.py` | Main CLI entry point — PDF → images → Claude vision → markdown |
| `requirements.txt` | Python dependencies (anthropic, pdf2image, Pillow) |
| `tests/test_translate.py` | Unit tests |

### Documentation
| File | Purpose |
|------|---------|
| `docs/product/decisions.md` | Architecture & product decisions log |
| `docs/product/plans/` | Sprint/feature plans |
| `docs/process/learnings.md` | Technical gotchas |
| `docs/process/retrospective.md` | Session retro logs |

## Technical Approach
- `pdf2image` converts each PDF page to a PIL image (JPEG)
- Claude vision API (claude-sonnet-4-6) receives the image and performs OCR + translation
- Handles two-column layout: left column first, then right
- Joins hyphenated line-break words (e.g., "Rud-\nnik" → "Rudnik")
- Transliterates proper nouns with Yiddish original in parentheses
- Labels image captions with [CAPTION]
- Supports `--pages 45-67` for re-running specific ranges
- Merges partial re-runs with existing output file

## Conventions

### Before Making Changes
- Read the relevant file(s) first
- Check `docs/product/decisions.md` for prior decisions on the topic
- Check `docs/process/learnings.md` when writing code that touches external services

### After Making Changes
- If the change involved a non-obvious decision, log it in `docs/product/decisions.md`
- If we learned something useful, add it to `docs/process/learnings.md`

### Code Style
- Prefer explicit over clever
- No unnecessary abstractions for one-time operations
- Clean up dead code created by your changes

@docs/process/learnings.md
