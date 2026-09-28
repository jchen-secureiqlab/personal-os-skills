# Deep Research Workflow

Create a NotebookLM notebook and populate it from multiple research angles — YouTube video search, NotebookLM web research, and user-provided sources. Optionally generate artifacts when research is complete.

## Inputs

- **topic**: Research topic (required)
- **notebook-title**: Override title (default: derived from topic)
- **queries**: Additional search queries beyond the topic (optional)
- **sources**: Additional files or URLs to include (optional)
- **artifacts**: Which artifacts to generate after research (optional, default: none)

## Step 1: Clarify Research Scope

If the user just says "research X", ask:
- How many YouTube queries to run (default: 3 — topic phrased 3 different ways)
- Whether to include web research via NotebookLM (default: yes, deep mode)
- Any specific files or URLs to include
- What artifacts to generate when done (audio, report, infographic, etc.)

## Step 2: Verify Auth

```bash
notebooklm status
```

If auth error: run `notebooklm login` to re-authenticate.

## Step 3: Create Notebook

```bash
notebooklm create "{notebook-title}" --json
notebooklm use {notebook_id}
```

Record `{notebook_id}` — needed for recovery if later steps fail.

## Step 4: YouTube Research

Uses the `youtube-search` skill to find relevant videos.

### 4a. Design queries — triangulate with 3-5 differently-framed queries

Each query should vary along a different axis to surface different perspectives:

1. **Direct/factual** — the topic verbatim (e.g., "Enhance MPP Turbo review")
2. **Explanatory/tutorial** — how-to framing (e.g., "Enhance MPP Turbo performance test")
3. **Critical/comparative** — contrarian angle (e.g., "Enhance MPP Turbo vs Joola Ben Johns")
4. **Expert/authority** (optional) — channel-qualified if known experts exist
5. **Recency-biased** (optional) — use `--after YYYY-MM-DD` for time-sensitive topics

### 4b. Run YouTube search

```bash
YT_RESULTS=$(mktemp /tmp/notebooklm-yt-XXXXXX.json)
python3 ~/.claude/skills/youtube-search/scripts/yt_search.py \
  --multi "{query1}" "{query2}" "{query3}" \
  --count 5 --transcripts --json > "$YT_RESULTS"
```

**If YouTube returns 0 results:** Skip to Step 5. Report: "YouTube search yielded 0 results for queries: [...]. Proceeding with web research only."

### 4c. Add YouTube videos as sources

**Tier 1: Native YouTube URL import (preferred).** NotebookLM natively supports YouTube URLs — it extracts metadata, chapters, and transcript automatically. Try this first:

```bash
notebooklm source add "https://youtube.com/watch?v={video_id}" --title "{video title}"
```

Pause 2-3 seconds between adds. If this succeeds, move to the next video. If it fails (age-restricted, private, no captions), fall to Tier 2.

**Tier 2: Text file upload (fallback).** For videos NotebookLM can't import natively, create a structured text source:

```bash
TEMP_DIR=$(mktemp -d /tmp/notebooklm-research-XXXXXX)
```

For videos **with transcripts** (from yt_search.py output): save full transcript + metadata as `.txt`.

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

**Error handling:** Track success/failure per video. If a source add fails, log it and continue.

**Rate limiting:** Pause 2-3 seconds between source adds. If rate limited, wait 60 seconds.

## Step 5: Web Research

### 5a. Check source count

```bash
notebooklm source list --json
```

NotebookLM source limits by plan: Standard=50, Plus=100, Pro=300. If approaching the limit, warn the user before adding web research sources.

### 5b. Run web research

```bash
notebooklm source add-research "{topic}" --mode deep --import-all --no-wait
```

For additional queries:
```bash
notebooklm source add-research "{query}" --mode deep --import-all --no-wait
```

Wait for all research to complete (deep mode can take several minutes):
```bash
notebooklm research wait --import-all
```

## Step 6: Add Additional Sources

If user provided files or URLs:

```bash
notebooklm source add "{file_or_url}"
```

Pause 2-3 seconds between adds.

## Step 7: Verify Sources

```bash
notebooklm source list --json
```

Report:
- Total sources by type (YouTube native, YouTube text fallback, web research, user files/URLs)
- Sources that failed (with reasons)
- Total source count vs. plan limit

**Gate check:** If source count is 0 (all adds failed), stop here. Do not proceed to artifact generation on an empty notebook. Report the errors and suggest checking auth or trying different sources.

## Step 8: Clean Up Temp Files

```bash
rm -rf "$TEMP_DIR" 2>/dev/null
rm -f "$YT_RESULTS" 2>/dev/null
```

## Step 9: Re-verify Auth (if 10+ minutes elapsed)

If significant time has passed since Step 2 (YouTube search + web research can take 10+ minutes):

```bash
notebooklm status
```

If auth expired: run `notebooklm login`, then continue.

## Step 10: Generate Artifacts (Optional)

If the user requested artifacts in Step 1:

### 10a. Verify sources are ready

```bash
notebooklm source list --json
```

Confirm sources have loaded (count > 0).

### 10b. Generate requested artifacts

For fast types (mind-map, report, infographic, slide-deck, quiz, flashcards):
```bash
notebooklm generate {type} "{description}" {options} --wait
```

For slow types (audio, video):
```bash
notebooklm generate {type} "{description}" {options} --retry 2
# Note task ID from output
notebooklm artifact wait {task_id}
```

**Timeout guidance:**
- mind-map: instant
- report, infographic, slide-deck, quiz, flashcards: 1-5 min
- audio: up to 10 min (deep-dive + long)
- video: up to 15 min

If generation times out: "Generation timed out but may still be in progress. Check with `notebooklm artifact list` in a few minutes."

### 10c. Download completed artifacts

```bash
notebooklm download {type} "{download-dir}/{notebook-slug}-{type}.{ext}" --latest
```

If generation fails: "Research completed successfully. Notebook ID: {notebook_id}. To retry artifact generation: `notebooklm generate {type} --wait`"

## Step 11: Summary

Report what was created:
- Notebook ID and title
- Source inventory: count by type, list of source titles
- Sources that failed (with reasons)
- Artifacts generated + download paths (if requested)
- Suggest next steps:
  - `notebooklm ask "question"` — Q&A against your sources
  - `notebooklm generate {type}` — generate more artifacts
  - Use the **import** workflow to bring sources into your Obsidian vault
  - Use the **ask** workflow for Q&A with citation resolution to vault

## Known Limitations

- **YouTube transcripts:** ~70-80% of English videos have auto-captions. Smaller channels and niche topics often lack captions entirely.
- **NotebookLM YouTube import:** May fail for age-restricted, private, or very new videos (captions processing can take up to 72 hours).
- **Source limits:** Standard plan = 50 sources per notebook. Budget sources carefully for large research projects.
- **Web research depth:** Deep mode finds more sources but takes longer (2-5 minutes per query). Fast mode is quicker but may miss relevant sources.
- **Rate limiting:** Rapid source uploads can trigger Google's rate limiter. The 2-3 second pause between adds mitigates this.

## Output

- Fully populated notebook at `{notebook_id}` with title `{notebook-title}`
- Sources from YouTube, web research, and user-provided files/URLs
- Artifacts downloaded (if requested)
- Ready for Q&A, more artifact generation, or vault import
