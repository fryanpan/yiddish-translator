# Yiddish Translator

A CLI tool to translate old Yiddish books (provided as PDFs) into English using Claude AI.

## Usage

```bash
python translate.py input.pdf output.md
```

This will:
1. Extract text from each page of the PDF
2. Translate each page from Yiddish to English using Claude AI
3. Save the translated output as a Markdown file

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here
```

## Requirements

- Python 3.9+
- An Anthropic API key (get one at https://console.anthropic.com)

## How It Works

The translator processes PDFs page by page to:
- Handle books of any length without hitting API limits
- Preserve page structure in the output
- Allow for partial recovery if a run is interrupted

Each page is translated independently, and the output includes page markers so you can easily navigate the translated text.

## Output Format

The output Markdown file has this structure:

```markdown
# Translation of: input.pdf

---

## Page 1

[English translation of page 1]

---

## Page 2

[English translation of page 2]

---
```
