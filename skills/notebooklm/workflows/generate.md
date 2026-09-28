# Generate Artifacts Workflow

Generate NotebookLM artifacts (audio, video, reports, infographics, mind-maps, etc.) and download them.

## Inputs

- **types**: Which artifact types to generate (required — ask if not specified)
- **description**: Custom instructions/prompt for generation (optional — this is the text you'd type in the NotebookLM UI)
- **download-dir**: Where to save downloads (default: `~/Downloads`)
- Type-specific options (see table below)

## Supported Types

| Type | Options | Duration |
|------|---------|----------|
| `audio` | `--format deep-dive\|brief\|critique\|debate`, `--length short\|default\|long` | 3-10 min |
| `video` | `--format explainer\|brief`, `--style auto\|classic\|whiteboard\|kawaii\|anime\|watercolor\|retro-print\|heritage\|paper-craft` | 5-15 min |
| `report` | `--format briefing-doc\|study-guide\|blog-post\|custom` | 1-3 min |
| `infographic` | `--orientation landscape\|portrait\|square`, `--detail concise\|standard\|detailed` | 1-3 min |
| `mind-map` | (no extra options) | instant |
| `slide-deck` | `--format detailed\|presenter`, `--length default\|short` | 2-5 min |
| `quiz` | `--quantity fewer\|standard\|more`, `--difficulty easy\|medium\|hard` | 1-2 min |
| `flashcards` | `--quantity fewer\|standard\|more`, `--difficulty easy\|medium\|hard` | 1-2 min |
| `data-table` | (description required) | 1-2 min |

## Step 1: Verify Context

```bash
notebooklm status
```

If no active notebook: ask user which one to use, then `notebooklm use {id}`.

If auth error: run `notebooklm login` to re-authenticate.

## Step 2: Check Notebook Has Sources

```bash
notebooklm source list --json
```

If source count is 0: stop. "This notebook has no sources. Add sources first before generating artifacts."

## Step 3: Generate Artifacts

**Strategy:** Start slow types first (they run server-side in parallel), then generate fast types while waiting.

### For multiple types requested:

```bash
# 1. Start slow types first (audio, video) — don't block
notebooklm generate audio "{description}" {options} --retry 2
notebooklm generate video "{description}" {options} --retry 2

# 2. Generate fast types while slow types process
notebooklm generate report "{description}" {options} --wait
notebooklm generate infographic "{description}" {options} --wait
notebooklm generate mind-map --wait

# 3. Wait for slow types to complete
notebooklm artifact list
# If still pending, wait:
notebooklm artifact wait {audio_task_id}
notebooklm artifact wait {video_task_id}
```

### For a single type:

```bash
# Fast types — use --wait
notebooklm generate {type} "{description}" {options} --wait

# Slow types (audio, video) — start and poll
notebooklm generate {type} "{description}" {options} --retry 2
# Note the task ID from output, then:
notebooklm artifact wait {task_id}
```

### Timeout handling

If `artifact wait` times out, the artifact may still be processing server-side:
- Check status: `notebooklm artifact list`
- If still `pending` or `in_progress`, wait a few more minutes and check again
- Report: "Generation timed out but may still be in progress. Check with `notebooklm artifact list` in a few minutes."

## Step 4: Download Artifacts

For each completed artifact:

```bash
notebooklm download {type} "{download-dir}/{slug}-{type}.{ext}" --latest
```

**File extensions by type:**
- audio → `.mp3`
- video → `.mp4`
- report → `.md`
- mind-map → `.json`
- infographic → `.png`
- slide-deck → `.pdf`
- data-table → `.csv`

**Note:** quiz and flashcards do not have downloadable files — they are displayed in the NotebookLM UI only.

## Step 5: Report Results

List all generated artifacts:
- Artifact title (assigned by NotebookLM)
- Type
- File path where downloaded
- File size
- Any failures or timeouts

## Output

- Downloaded artifact files in `{download-dir}/`
- Artifact metadata displayed for reference
