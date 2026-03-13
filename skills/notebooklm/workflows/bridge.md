# Pipeline Bridge Workflow

Import research output from a LinkedIn content pipeline run into NotebookLM for deeper exploration, Q&A, and artifact generation.

## Inputs

- **run-dir**: Path to a pipeline run directory (e.g., `~/projects/notebooklm-cc/output/2026-03-13-run-001/`)
- **notebook-id**: Existing notebook ID to import into (optional)
- **title**: Title for a new notebook (optional — used with `--create`)

One of `--notebook-id` or `--create` is required.

## Step 1: Verify Auth

```bash
notebooklm status
```

If auth error: run `notebooklm login` to re-authenticate.

## Step 2: Verify Run Directory

Check that the run directory exists and contains research files:

```bash
ls {run-dir}/02b-verified-research.md 2>/dev/null || ls {run-dir}/02-research.md 2>/dev/null
```

The bridge prefers `02b-verified-research.md` (fact-checked). Falls back to `02-research.md` if verified doesn't exist.

**Skipped files:** Draft (`03-draft.md`) and critique (`04a-d-*.md`) are pipeline outputs, not research sources — they are intentionally not imported.

## Step 3: Run Bridge

### Into existing notebook:

```bash
python3 .claude/skills/notebooklm/scripts/pipeline_bridge.py \
  --notebook-id {notebook-id} \
  "{run-dir}"
```

### Into new notebook:

```bash
python3 .claude/skills/notebooklm/scripts/pipeline_bridge.py \
  --create "{title}" \
  "{run-dir}"
```

The bridge:
1. Reads the best available research file (verified preferred)
2. Imports it as a text source titled `"Research: {topic} (verified)"` or `"Research: {topic}"`
3. Writes `bridge-manifest.json` in the run directory for idempotency
4. Prints URL import deferral notice (discover schema not yet defined)

**Idempotency:** Re-running the bridge skips already-imported sources (checked against manifest).

## Step 4: Verify Import

```bash
notebooklm source list
```

Confirm the research source appears in the notebook.

## Step 5: Suggest Next Steps

- **Add more sources** to deepen research beyond what the pipeline found
- **Generate artifacts** — `notebooklm generate audio` for a podcast, `notebooklm generate report` for a summary
- **Ask questions** the pipeline didn't explore — use the **ask** workflow
- **Import to vault** — use the **import** workflow to bring everything into Obsidian

## Output

- Research imported into NotebookLM notebook (new or existing)
- `bridge-manifest.json` written for idempotent re-runs
- Ready for Q&A, artifact generation, or vault import
