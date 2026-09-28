# Create Notebook Workflow

Create a new NotebookLM notebook, set it as active, and optionally add sources.

## Inputs

- **title**: Notebook title (required — ask user if not provided)
- **sources**: List of files, URLs, YouTube links, or search queries to add (optional)

## Step 1: Verify Auth

```bash
notebooklm status
```

If auth error: run `notebooklm login` to re-authenticate.

## Step 2: Create Notebook

```bash
notebooklm create "{title}" --json
```

Parse JSON output to get `notebook_id`.

## Step 3: Set as Active

```bash
notebooklm use {notebook_id}
```

## Step 4: Add Sources (if provided)

For each source, detect type and add. Pause 2-3 seconds between calls to avoid rate limiting.

Track success/failure count for each source.

**Files** (validates extension: `.pdf`, `.txt`, `.md`, `.docx`, `.csv`):
```bash
notebooklm source add /path/to/file.pdf
```

**URLs** (web articles):
```bash
notebooklm source add "https://example.com/article"
```

**YouTube URLs** (prefer native import — NotebookLM extracts metadata + transcript):
```bash
notebooklm source add "https://youtube.com/watch?v=..."
```

**Web research queries:**
```bash
notebooklm source add-research "query" --mode deep --import-all
```

**Error handling:** If a source add fails (paywall, empty content, unsupported format), log it and continue with the next source. Do not abort the workflow.

**Rate limiting:** If any add returns a rate limit error, wait 60 seconds before resuming.

## Step 5: Verify

```bash
notebooklm source list
```

Report:
- Notebook ID and title
- Total sources added vs. requested
- Any failures with reasons
- Suggest next steps: "ask" for Q&A, "generate" for artifacts, "research" for more sources

## Output

- Active notebook at `{notebook_id}` with title `{title}`
- Sources loaded (count and types)
- Ready for ask, generate, research, or import workflows
