---
title: "feat: Add create, research, and generate workflows to notebooklm skill"
type: feat
date: 2026-03-05
deepened: 2026-03-05
---

# Add Create, Research, and Generate Workflows to NotebookLM Skill

## Enhancement Summary

**Deepened on:** 2026-03-05
**Research agents used:** skill-pattern analysis, deep-research workflow design, edge-case review

### Key Improvements
1. **YouTube source strategy**: Prefer native YouTube URL import via `source add https://youtube.com/...` (NotebookLM processes these natively with metadata). Fall back to transcript text upload only for videos NotebookLM can't import.
2. **Rate limiting & source limits**: Added delays between source uploads (2-3s), batch pattern, and source count checks against plan limits (Standard: 50, Plus: 100, Pro: 300).
3. **Query triangulation**: 3-5 queries per topic, each framed along a different axis (factual, explanatory, critical) based on research methodology best practices.
4. **Error recovery**: Auth re-check before generation phase, graceful fallthrough when YouTube returns 0 results, per-source error tracking.
5. **Inline generation steps**: Research workflow inlines artifact generation rather than cross-referencing generate.md, preserving context.
6. **Timeout handling**: Audio/video use extended timeouts; fallback to manual polling if `--wait` times out.

---

## Overview

The notebooklm skill currently only has two workflows: **import** (sources → Obsidian vault) and **ask** (Q&A with citation resolution). This leaves the full notebook lifecycle uncovered — creating notebooks, populating them with research, and generating artifacts all require raw CLI commands.

This plan adds three new workflows that wrap `notebooklm-py` CLI commands into the same step-by-step format used by the existing workflows:

| Workflow | Trigger | What it does |
|---|---|---|
| `create.md` | "notebooklm create", "new notebook" | Create notebook + add sources (files, URLs, web research) |
| `research.md` | "notebooklm research", "deep research" | Multi-source deep research: YouTube search + web research + file/URL sources → notebook |
| `generate.md` | "notebooklm generate", "make infographic" | Generate artifacts (audio, video, report, infographic, mind-map) + download |

## Problem Statement

Users must know the exact `notebooklm-py` CLI syntax to:
- Create a notebook and add sources to it
- Perform deep research combining YouTube transcripts with web sources
- Generate and download artifacts (audio, video, reports, infographics, mind-maps)

The skill should handle this orchestration so users can say "research X deeply" and get a fully populated notebook.

## Proposed Solution

Three new workflow files following the existing conventions (step-by-step markdown, bash commands, input derivation from context). The **research** workflow is the most ambitious — it combines the `youtube-search` skill with `notebooklm source add-research` to triangulate across YouTube and web sources.

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `workflows/create.md` | **NEW** | Create notebook + add sources |
| `workflows/research.md` | **NEW** | Deep multi-source research workflow |
| `workflows/generate.md` | **NEW** | Generate + download artifacts |
| `SKILL.md` | **MODIFY** | Add trigger phrases + routing table entries |

---

## Technical Approach

### Workflow 1: `create.md` — Create Notebook

**Trigger phrases:** "notebooklm create", "new notebook", "create notebook"

**Inputs:**
- `title`: Notebook title (required — ask user if not provided)
- `sources`: List of files, URLs, or search queries to add (optional)

**Steps:**

1. **Verify auth**
   ```bash
   notebooklm status
   ```
   If auth error: run `notebooklm login` to re-authenticate.

2. **Create notebook**
   ```bash
   notebooklm create "{title}" --json
   ```
   Parse JSON output to get `notebook_id`.

3. **Set as active**
   ```bash
   notebooklm use {notebook_id}
   ```

4. **Add sources** (if provided)
   For each source, detect type and add:
   ```bash
   # Files (validates extension: .pdf, .txt, .md, .docx, .csv)
   notebooklm source add /path/to/file.pdf

   # URLs (web articles, YouTube videos)
   notebooklm source add "https://example.com/article"

   # YouTube URLs — prefer native import (NotebookLM extracts metadata + transcript)
   notebooklm source add "https://youtube.com/watch?v=..."

   # Web research
   notebooklm source add-research "query" --mode deep --import-all
   ```

   **Error handling:** Wrap each `source add` call individually. Track success/failure count. If a source fails (paywall, empty content, unsupported format), log it and continue. Report at end: "Added 7/10 sources (3 failed: [reasons])."

   **Rate limiting:** Add a 2-3 second pause between sequential `source add` calls to avoid hitting Google's rate limiter. If any add returns a rate limit error, wait 60 seconds before resuming.

5. **Verify**
   ```bash
   notebooklm source list
   ```

**Output:** Active notebook with sources loaded, ready for ask/generate workflows.

---

### Workflow 2: `research.md` — Deep Multi-Source Research

**Trigger phrases:** "notebooklm research", "deep research", "research topic"

This is the flagship workflow. It creates a notebook, populates it from multiple research angles (YouTube + web), and optionally generates artifacts.

**Inputs:**
- `topic`: Research topic (required)
- `notebook-title`: Override title (default: derived from topic)
- `queries`: Additional search queries beyond the topic (optional)
- `sources`: Additional files or URLs to include (optional)
- `artifacts`: Which artifacts to generate after research (optional, default: none)

**Steps:**

1. **Clarify research scope**
   If the user just says "research X", ask:
   - How many YouTube queries to run (default: 3 — topic phrased 3 different ways)
   - Whether to include web research via NotebookLM (default: yes, deep mode)
   - Any specific files or URLs to include
   - What artifacts to generate when done (audio, report, infographic, etc.)

2. **Verify auth**
   ```bash
   notebooklm status
   ```
   If auth error: run `notebooklm login` to re-authenticate.

3. **Create notebook**
   ```bash
   notebooklm create "{notebook-title}" --json
   notebooklm use {notebook_id}
   ```

4. **YouTube research** (uses youtube-search skill)

   **Query strategy — triangulate with 3-5 differently-framed queries:**
   Each query should vary along a different axis to surface different expert communities:
   - **Direct/factual** — the topic verbatim (e.g., "Enhance MPP Turbo review")
   - **Explanatory/tutorial** — how-to framing (e.g., "Enhance MPP Turbo performance test")
   - **Critical/comparative** — contrarian angle (e.g., "Enhance MPP Turbo vs Joola Ben Johns")
   - **Expert/authority** (optional) — channel-qualified if known experts exist
   - **Recency-biased** (optional) — use `--after` for time-sensitive topics

   Run multi-query YouTube search:
   ```bash
   YT_RESULTS=$(mktemp /tmp/notebooklm-yt-XXXXXX.json)
   python3 ~/.claude/skills/youtube-search/scripts/yt_search.py \
     --multi "{query1}" "{query2}" "{query3}" \
     --count 5 --transcripts --json > "$YT_RESULTS"
   ```

   **Source strategy — two tiers:**

   **Tier 1: Native YouTube URL import (preferred).** NotebookLM natively supports YouTube URLs and extracts metadata + transcript automatically. Try this first for each video:
   ```bash
   notebooklm source add "https://youtube.com/watch?v={video_id}" --title "{video title}"
   ```
   If this succeeds, move to the next video. If it fails (age-restricted, private, no transcript), fall to Tier 2.

   **Tier 2: Text file upload (fallback).** For videos NotebookLM can't import natively, create a structured text source from available metadata:
   ```bash
   TEMP_DIR=$(mktemp -d /tmp/notebooklm-research-XXXXXX)
   ```

   For videos **with transcripts** (from yt_search.py): save full transcript + metadata as `.txt`.
   For videos **without transcripts**: save structured metadata note:
   ```
   # {Video Title}
   - Channel: {channel} ({subscriber_count} subscribers)
   - Published: {date} | Duration: {duration}
   - Views: {views} | Likes: {likes}
   - URL: {url}

   ## Description
   {full description text}

   ## Chapters
   {timestamp - chapter title list}

   ## Research Note
   Source included as metadata only (transcript unavailable).
   Confidence: LOW — verify claims against transcript-available sources.
   ```

   Upload each fallback file:
   ```bash
   notebooklm source add "$TEMP_DIR/yt-source-{N}.txt" --title "{video title}"
   ```

   **Rate limiting:** Pause 2-3 seconds between source add calls.

   **If YouTube returns 0 results:** Skip YouTube phase entirely. Report: "YouTube search yielded 0 results for queries: [...]. Proceeding with web research only."

5. **Web research** via NotebookLM's built-in search

   **Check source count before adding more:**
   ```bash
   notebooklm source list --json
   ```
   NotebookLM source limits by plan: Standard=50, Plus=100, Pro=300. If approaching the limit, warn the user before adding web research sources.

   ```bash
   notebooklm source add-research "{topic}" --mode deep --import-all --no-wait
   ```
   For additional queries:
   ```bash
   notebooklm source add-research "{query}" --mode deep --import-all --no-wait
   ```
   Wait for all research to complete (allow up to 10 minutes for deep mode):
   ```bash
   notebooklm research wait --import-all
   ```

6. **Add additional sources** (if user provided files/URLs)
   ```bash
   notebooklm source add "{file_or_url}"
   ```

7. **Verify sources**
   ```bash
   notebooklm source list --json
   ```
   Report: total sources, breakdown by type (YouTube, web, file), any failures.

   **Gate check:** If source count is 0 (all adds failed), stop here. Do not proceed to artifact generation on an empty notebook. Report the errors and suggest the user check auth or try different sources.

8. **Clean up temp files**
   ```bash
   rm -rf "$TEMP_DIR"
   rm -f "$YT_RESULTS"
   ```

9. **Re-verify auth** (if 10+ minutes have elapsed since Step 2)
   ```bash
   notebooklm status
   ```
   If auth expired: run `notebooklm login`, then continue.

10. **Generate artifacts** (if requested in Step 1)

    Inline the generation steps here (do NOT delegate to `generate.md` — keeps context intact):

    For each requested artifact type:
    ```bash
    # Start generation (don't use --wait for audio/video — timeout too short)
    TASK_ID=$(notebooklm generate {type} "{description}" {options} --json | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

    # Wait with appropriate timeout
    notebooklm artifact wait "$TASK_ID"

    # Download
    notebooklm download {type} "{download-dir}/{notebook-slug}-{type}.{ext}" --latest
    ```

    **Timeout guidance:**
    - mind-map: instant (no wait needed)
    - report, infographic, slide-deck, quiz, flashcards: ~1-3 minutes
    - audio: up to 10 minutes (deep-dive + long format)
    - video: up to 15 minutes

    If generation times out, the artifact may still be processing server-side. Report: "Generation timed out but may still be in progress. Check with `notebooklm artifact list` in a few minutes."

    If generation fails, report: "Research completed successfully. Notebook ID: {id}. To retry artifact generation: `notebooklm generate {type} --wait`"

11. **Summary**
    Report what was created:
    - Notebook ID and title
    - Source count by type (YouTube native, YouTube text, web research, user files/URLs)
    - Sources that failed (with reasons)
    - Artifacts generated + download paths
    - Suggest next steps: "ask" for Q&A, "generate" for more artifacts, "import" to vault

**Output:** Fully populated notebook ready for Q&A, artifact generation, or vault import.

---

### Workflow 3: `generate.md` — Generate & Download Artifacts

**Trigger phrases:** "notebooklm generate", "make infographic", "generate audio", "generate report", "download artifact"

**Inputs:**
- `types`: Which artifact types to generate (required — ask if not specified)
- `description`: Custom instructions/prompt for generation (optional)
- `download-dir`: Where to save downloads (default: `~/Downloads`)
- Type-specific options (orientation, format, detail level, etc.)

**Supported types and their options:**

| Type | Options | Typical Duration |
|------|---------|-----------------|
| `audio` | `--format deep-dive\|brief\|critique\|debate`, `--length short\|default\|long` | 3-10 min |
| `video` | `--format explainer\|brief`, `--style auto\|classic\|whiteboard\|kawaii\|anime\|watercolor\|retro-print\|heritage\|paper-craft` | 5-15 min |
| `report` | `--format briefing-doc\|study-guide\|blog-post\|custom` | 1-3 min |
| `infographic` | `--orientation landscape\|portrait\|square`, `--detail concise\|standard\|detailed` | 1-3 min |
| `mind-map` | (no extra options) | instant |
| `slide-deck` | `--format detailed\|presenter`, `--length default\|short` | 2-5 min |
| `quiz` | `--quantity fewer\|standard\|more`, `--difficulty easy\|medium\|hard` | 1-2 min |
| `flashcards` | `--quantity fewer\|standard\|more`, `--difficulty easy\|medium\|hard` | 1-2 min |

**Steps:**

1. **Verify context**
   ```bash
   notebooklm status
   ```
   If no active notebook, ask user which one to use.
   If auth error: run `notebooklm login` to re-authenticate.

2. **Check notebook has sources**
   ```bash
   notebooklm source list --json
   ```
   If source count is 0, stop: "This notebook has no sources. Add sources first before generating artifacts."

3. **Generate each artifact**

   For fast types (mind-map, report, infographic, quiz, flashcards, slide-deck):
   ```bash
   notebooklm generate {type} "{description}" {options} --wait
   ```

   For slow types (audio, video) — start without `--wait`, then poll:
   ```bash
   notebooklm generate {type} "{description}" {options} --retry 2
   # Note the task ID from output
   notebooklm artifact wait {task_id}
   ```

   If multiple types requested, start all slow types first (they run server-side in parallel), then generate fast types while waiting:
   ```bash
   # Start slow types first
   notebooklm generate audio "{description}" --retry 2
   notebooklm generate video "{description}" --retry 2

   # Generate fast types while audio/video process
   notebooklm generate report "{description}" --wait
   notebooklm generate infographic "{description}" --orientation portrait --wait

   # Now wait for slow types
   notebooklm artifact list  # check status
   ```

4. **Download artifacts**
   For each completed artifact:
   ```bash
   notebooklm download {type} "{download-dir}/{notebook-slug}-{type}.{ext}" --latest
   ```

   File extensions by type:
   - audio → `.mp3`
   - video → `.mp4`
   - report → `.md`
   - mind-map → `.json`
   - infographic → `.png`
   - slide-deck → `.pdf`
   - data-table → `.csv`
   - quiz → (no download — displayed in-app)
   - flashcards → (no download — displayed in-app)

5. **Report results**
   List all generated artifacts with:
   - Artifact title (assigned by NotebookLM)
   - File path where downloaded
   - File size
   - Any failures or timeouts

**Output:** Downloaded artifact files in the specified directory.

---

### SKILL.md Updates

Add new entries to the workflow routing table:

```markdown
## Workflow Routing

| User says | Workflow |
|-----------|----------|
| "import notebook", "notebooklm import", "import sources" | [workflows/import.md](workflows/import.md) |
| "notebooklm ask", "ask notebook", "Q&A" | [workflows/ask.md](workflows/ask.md) |
| "notebooklm create", "new notebook", "create notebook" | [workflows/create.md](workflows/create.md) |
| "notebooklm research", "deep research", "research topic" | [workflows/research.md](workflows/research.md) |
| "notebooklm generate", "make infographic", "generate audio", "generate report" | [workflows/generate.md](workflows/generate.md) |
```

Update the `description` in SKILL.md frontmatter to include the new trigger phrases:

```yaml
description: >-
  Full NotebookLM lifecycle — create notebooks, deep research (YouTube + web),
  generate artifacts (audio, video, reports, infographics), import to Obsidian vault,
  Q&A with citation resolution. Use when user says "notebooklm create", "notebooklm research",
  "deep research", "notebooklm generate", "make infographic", "generate audio",
  "notebooklm import", "notebooklm ask", or wants to turn research into vault knowledge.
```

---

## Acceptance Criteria

### Functional Requirements

- [ ] `workflows/create.md` — creates notebook, sets context, adds sources (files, URLs, web research)
- [ ] `workflows/research.md` — full deep research pipeline: YouTube multi-query + web research + optional artifacts
- [ ] `workflows/generate.md` — generates any artifact type with custom instructions and downloads result
- [ ] `SKILL.md` — updated routing table, trigger phrases, and description in frontmatter
- [ ] All workflows follow existing conventions: numbered steps, bash code blocks, input derivation, verify step
- [ ] All workflows start with auth verification via `notebooklm status`
- [ ] Research workflow integrates youtube-search skill at `~/.claude/skills/youtube-search/scripts/yt_search.py`
- [ ] Research workflow prefers native YouTube URL import, falls back to text file upload
- [ ] Research workflow handles both transcript-available and transcript-unavailable YouTube videos
- [ ] Generate workflow supports all artifact types with their type-specific options
- [ ] Generate workflow parallelizes slow types (audio, video) while running fast types

### Error Handling Requirements

- [ ] Per-source error tracking with success/failure count reporting
- [ ] Rate limiting: 2-3s delay between source adds, exponential backoff on rate limit errors
- [ ] Source count check before bulk adds (warn at Standard plan limit of 50)
- [ ] Gate check: do not generate artifacts on empty notebook (0 sources)
- [ ] Auth re-check before generation phase if 10+ minutes elapsed
- [ ] YouTube 0 results: fall through to web research only, report to user
- [ ] Generation timeout: report that artifact may still be processing, suggest `artifact list` check

### Security Requirements

- [ ] All notebook slugs validated through `shared.py:validate_slug()` where applicable
- [ ] Temp files use `mktemp` pattern — both files and directories (`mktemp -d`)
- [ ] No hardcoded `/tmp/` paths
- [ ] File paths use safe_filename() for user-provided titles in download filenames
- [ ] Temp directory cleanup at end of research workflow

### Quality Gates

- [ ] Existing import and ask workflows unchanged
- [ ] New workflows tested manually end-to-end with a real notebook
- [ ] SKILL.md trigger phrases don't conflict with existing ones

---

## Implementation Phases

### Phase 1: Create + Generate workflows
Simpler workflows that directly wrap CLI commands. Validate the step format and conventions.

**Files:**
- `workflows/create.md`
- `workflows/generate.md`
- `SKILL.md` (partial update)

### Phase 2: Research workflow
The complex workflow integrating YouTube search + web research + source upload.

**Files:**
- `workflows/research.md`
- `SKILL.md` (final update)

### Phase 3: Manual testing
Run each workflow end-to-end against a real NotebookLM notebook to verify the full pipeline.

**Test scenarios:**
1. `create` — create notebook with 2 PDF files + 1 URL
2. `research` — research a niche topic (expect some YouTube failures), verify fallback to web research
3. `research` — research a popular topic with YouTube transcripts available, verify native URL import
4. `generate` — generate audio + infographic with custom instructions, verify download
5. `generate` — generate on empty notebook, verify gate check blocks it

---

## References

### Internal References

- Existing workflow patterns: `skills/notebooklm/workflows/import.md`, `skills/notebooklm/workflows/ask.md`
- Shared utilities: `skills/notebooklm/scripts/shared.py`
- YouTube search skill: `~/.claude/skills/youtube-search/scripts/yt_search.py`
- Full CLI reference: `~/projects/notebooklm-py/src/notebooklm/cli/` (generate.py, source.py, notebook.py)
- NotebookLM exceptions: `~/projects/notebooklm-py/src/notebooklm/exceptions.py` (SourceAddError, RateLimitError, AuthError)

### External References

- [NotebookLM source limits](https://medium.com/ai-quick-tips/notebooklm-limits-explained-free-vs-pro-what-you-actually-get-1625db4ac6dc): Standard=50, Plus=100, Pro=300, Ultra=600
- [YouTube transcript + NotebookLM integration](https://www.transcribr.io/blog/youtube-transcripts-notebooklm)
- [Query triangulation methodology](https://www.scribbr.com/methodology/triangulation/): 3+ independent sources for validation
- [Deep research agent architecture](https://arxiv.org/html/2508.12752v1): query planning → acquisition → memory → synthesis

### CLI Command Quick Reference

```bash
# Create
notebooklm create "{title}" --json
notebooklm use {id}

# Sources
notebooklm source add {file_or_url} [--title "..."]
notebooklm source add "https://youtube.com/watch?v=..." [--title "..."]
notebooklm source add-research "{query}" --mode deep --import-all [--no-wait]
notebooklm research wait --import-all
notebooklm source list [--json]

# Generate
notebooklm generate {type} [description] [options] [--wait] [--retry N]
notebooklm download {type} [output_path] [--latest]

# Artifacts
notebooklm artifact list
notebooklm artifact wait {id}

# Auth
notebooklm status
notebooklm login
```
