# Learnings

Technical discoveries that should persist across sessions.

## PyMuPDF (fitz)
- Import as `import fitz` — the package is called `pymupdf` in requirements but imported as `fitz`
- `page.get_text()` returns plain text; for better layout preservation use `page.get_text("blocks")`
- Old Yiddish books scanned as images won't have extractable text — OCR would be needed (future enhancement)

## Claude API (Yiddish Translation)
- Model `claude-sonnet-4-6` handles Yiddish well — it understands the Hebrew script used for Yiddish
- `max_tokens=4096` is sufficient for a typical book page; dense pages may need more
- Yiddish uses right-to-left Hebrew characters; PDF extraction preserves the characters but may have ordering issues on some scanned documents
