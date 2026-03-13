---
name: notebooklm
description: >-
  Full NotebookLM lifecycle — create notebooks, deep research (YouTube + web),
  generate artifacts (audio, video, reports, infographics), import to Obsidian vault,
  Q&A with citation resolution, pipeline bridge. Use when user says "notebooklm create",
  "new notebook", "notebooklm research", "deep research", "research topic",
  "notebooklm generate", "make infographic", "generate audio", "generate report",
  "generate video", "notebooklm import", "import notebook", "notebooklm ask",
  "ask notebook", "Q&A", "notebooklm bridge", "import pipeline",
  or wants to turn research into vault knowledge.
---

# NotebookLM — Research, Generate, Knowledge

Full NotebookLM lifecycle: create notebooks, deep research (YouTube + web), generate artifacts (audio, video, reports, infographics, mind-maps), import to Obsidian vault as linked knowledge graphs, Q&A with citation resolution.

## Prerequisites

### 1. Install notebooklm-py

```bash
cd ~/projects/notebooklm-py
uv sync --extra browser
uv run playwright install chromium
```

### 2. Authenticate

```bash
notebooklm login
```

Opens a browser window - log in with your Google account. Cookies are saved to `~/.notebooklm/storage_state.json`.

Re-run `notebooklm login` when cookies expire (you'll see auth errors).

### 3. Obsidian Plugins

- **Dataview** (required) - citation tables and dashboard queries use Dataview/DataviewJS

### 4. Vault Setup

Copy the templates from `templates/` into your vault:
- `templates/notebook-source.md` -> `Templates/Types/notebook-source.md`
- `templates/dashboard.md` -> use as reference when creating dashboards

## Quick Start

```bash
# Check current notebook
notebooklm status

# Switch notebook
notebooklm use <notebook-id>

# List notebooks
notebooklm list
```

## Workflow Routing

| User says | Workflow |
|-----------|----------|
| "notebooklm create", "new notebook", "create notebook" | [workflows/create.md](workflows/create.md) |
| "notebooklm research", "deep research", "research topic" | [workflows/research.md](workflows/research.md) |
| "notebooklm generate", "make infographic", "generate audio", "generate report", "generate video" | [workflows/generate.md](workflows/generate.md) |
| "import notebook", "notebooklm import", "import sources" | [workflows/import.md](workflows/import.md) |
| "notebooklm ask", "ask notebook", "Q&A", "follow up", "deep dive" | [workflows/ask.md](workflows/ask.md) |
| "notebooklm bridge", "import pipeline", "bridge research" | [workflows/bridge.md](workflows/bridge.md) |

## Architecture

```
Your Vault
├── Notes/NotebookLM/{notebook-slug}/
│   ├── Sources/          # One .md per source (YouTube, PDF, web, etc.)
│   │   ├── Video Title.md
│   │   └── Article Title.md
│   └── QA/               # Q&A notes with resolved citations
│       └── 2026-02-23 Emerging Themes.md
└── Notes/Dashboards/
    └── My Research.md     # Dashboard with Dataview queries
```

- **Source files** have type `notebook-source` with frontmatter: `source_id`, `notebook_id`, `url`, `source_type`, topics as `[[wikilinks]]`
- **Q&A notes** have type `reference` with `[N]` citations resolved to `[[Source Title#Passage N]]` wikilinks
- **Dashboards** use Dataview queries to list sources and Q&A notes

## Data Model

**notebook-source frontmatter:**
```yaml
type: notebook-source
source_id: "uuid"        # NotebookLM source ID
notebook_id: "uuid"      # NotebookLM notebook ID
url: ""                  # Original URL
source_type: youtube     # youtube, pdf, web, text, gdocs, gslides
status: active
date: YYYY-MM-DD
topics:
  - "[[Topic Name]]"     # AI-extracted topics as wikilinks
related:
  - "[[Notes/Dashboards/Dashboard Name]]"
```

**Q&A reference frontmatter:**
```yaml
type: reference
status: current
date: YYYY-MM-DD
source: "notebooklm:{notebook-slug}"
related:
  - "[[Notes/Dashboards/Dashboard Name]]"
```

## Scripts

All scripts use the `notebooklm-py` Python API directly (no CLI subprocess calls). They require `notebooklm-py` to be importable — `shared.py` handles `sys.path` resolution automatically.

| Script | Purpose |
|--------|---------|
| `scripts/import_sources.py` | Import sources as vault files with AI-generated guides and topics |
| `scripts/extract_passages.py` | Extract cited passages from Q&A into source files |
| `scripts/resolve_citations.py` | Replace `[N]` markers with `[[wikilinks]]` in Q&A answers |
| `scripts/ask_notebook.py` | Ask questions with conversation threading, outputs JSON with `conversation_id` |
| `scripts/pipeline_bridge.py` | Import pipeline research output into NotebookLM |
| `scripts/shared.py` | Shared utilities: slug validation, filename sanitization, retry helper, import guard |

All scripts use `Path.cwd()` as vault root — run them from your vault directory.

**Vault path flexibility:** `import_sources.py`, `extract_passages.py`, and `resolve_citations.py` accept `--vault-path` (default: `Notes/NotebookLM`) and `--dashboard-path` (default: `Notes/Dashboards`) to support any vault layout (e.g., PARA-style `30_Sources/NotebookLM`).
