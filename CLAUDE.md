# Project: yiddish-translator

## Overview
A CLI tool to translate Yiddish PDF books into English using the Claude AI API.
The tool processes PDFs page by page and outputs a Markdown file with the full translation.

## Architecture

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the translator
python translate.py input.pdf output.md

# Run tests
python -m pytest tests/
```

### Key Files

| File | Purpose |
|------|---------|
| `translate.py` | Main CLI entry point — PDF extraction + translation |
| `requirements.txt` | Python dependencies (anthropic, pymupdf) |
| `tests/test_translate.py` | Unit tests |

### Documentation
| File | Purpose |
|------|---------|
| `docs/product/decisions.md` | Architecture & product decisions log |
| `docs/product/plans/` | Sprint/feature plans |
| `docs/process/learnings.md` | Technical gotchas |
| `docs/process/retrospective.md` | Session retro logs |

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
