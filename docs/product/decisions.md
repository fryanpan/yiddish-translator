# Architecture & Product Decisions

## 2026-04-04 — Initial Architecture

**Decision:** Process PDFs page by page rather than all at once.
**Why:** Avoids hitting Claude API token limits for long books; allows partial recovery if a run is interrupted.

**Decision:** Output as Markdown with `## Page N` headings.
**Why:** Markdown is human-readable, easy to navigate, and works with standard tools. Headers make it easy to jump to specific pages.

**Decision:** Use PyMuPDF (fitz) for PDF text extraction.
**Why:** Best Python library for PDF text extraction; handles Unicode (including Yiddish Hebrew script) correctly; actively maintained.

**Decision:** Single-file CLI (`translate.py`) rather than a package.
**Why:** This is a simple tool with one purpose. A single file is easier to run and understand for non-technical users.
