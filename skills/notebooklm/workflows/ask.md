# Ask Notebook Workflow

Ask a NotebookLM notebook questions with conversation threading for iterative deep-dives. Save answers as vault reference notes with `[N]` citations resolved to `[[wikilinks]]`.

## Inputs

- **question**: The question to ask
- **notebook-id**: NotebookLM notebook ID
- **title**: Short title for the Q&A note (e.g. "Emerging Themes Across 20 Videos")
- **notebook-slug**: Which notebook folder to use in the vault
- **dashboard-title**: Dashboard to link to via `related`
- **mode**: Chat mode — `default`, `learning-guide`, `concise`, `detailed` (optional)
- **persona**: Custom persona prompt (optional, overrides mode)
- **conversation-id**: For follow-up questions (optional — from previous output)
- **vault-path**: Vault subfolder for sources (optional, default: `Notes/NotebookLM`)
- **dashboard-path**: Vault subfolder for dashboards (optional, default: `Notes/Dashboards`)

**Python interpreter:** All script commands below must use `~/projects/notebooklm-py/.venv/bin/python3` (not system `python3`), since the scripts depend on `httpx` and other packages installed in the notebooklm-py venv.

## Step 1: Verify Auth

```bash
notebooklm status
```

If auth error: run `notebooklm login` to re-authenticate.

## Step 2: Ask the Question

### First question (new conversation):

```bash
QA_FILE=$(mktemp /tmp/notebooklm-qa-XXXXXX.json)
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/ask_notebook.py \
  --notebook-id {notebook-id} \
  --question "{question}" \
  --mode {mode} > "$QA_FILE"
```

### Follow-up question (existing conversation):

```bash
QA_FILE_2=$(mktemp /tmp/notebooklm-qa-XXXXXX.json)
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/ask_notebook.py \
  --notebook-id {notebook-id} \
  --question "{follow-up question}" \
  --conversation-id {conversation_id} > "$QA_FILE_2"
```

The `conversation_id` comes from the previous question's JSON output. The server maintains the conversation thread — follow-ups have access to prior context.

### With custom persona:

```bash
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/ask_notebook.py \
  --notebook-id {notebook-id} \
  --question "{question}" \
  --persona "You are a security analyst. Focus on risks and mitigations." > "$QA_FILE"
```

### With response length:

```bash
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/ask_notebook.py \
  --notebook-id {notebook-id} \
  --question "{question}" \
  --response-length longer > "$QA_FILE"
```

**Output JSON format:**
```json
{
  "answer": "The answer text with [1] citation markers...",
  "conversation_id": "uuid-for-follow-ups",
  "turn_number": 1,
  "is_follow_up": false,
  "references": [
    {"source_id": "uuid", "cited_text": "...", "citation_number": 1}
  ]
}
```

## Step 3: Extract Passages

```bash
SOURCES_FILE=$(mktemp /tmp/notebooklm-sources-XXXXXX.json)
notebooklm source list --json > "$SOURCES_FILE"

PASSAGE_MAP=$(mktemp /tmp/notebooklm-passages-XXXXXX.json)
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/extract_passages.py \
  --qa "$QA_FILE" \
  --sources "$SOURCES_FILE" \
  --slug {notebook-slug} \
  --vault-path "{vault-path}" > "$PASSAGE_MAP"
```

This writes `## Cited Passages / ### Passage N` sections into source files using the `cited_text` from references. Idempotent — skips sources that already have passages.

**Multi-turn:** Pass all Q&A files to accumulate passages across turns:

```bash
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/extract_passages.py \
  --qa "$QA_FILE" "$QA_FILE_2" \
  --sources "$SOURCES_FILE" \
  --slug {notebook-slug} \
  --vault-path "{vault-path}" > "$PASSAGE_MAP"
```

## Step 4: Resolve Citations

```bash
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/resolve_citations.py \
  --qa "$QA_FILE" \
  --sources "$SOURCES_FILE" \
  --slug {notebook-slug} \
  --passages "$PASSAGE_MAP" \
  --title "{title}" \
  --dashboard "{dashboard-title}" \
  --vault-path "{vault-path}" \
  --dashboard-path "{dashboard-path}" \
  --output "{vault-path}/{notebook-slug}/QA/{date} {title}.md"
```

This:
1. Deduplicates references by `cited_text` to find unique evidence chunks
2. Maps answer `[N]` to the Nth unique chunk (not to `citation_number` field)
3. Expands citation specs (`[1, 2]`, `[3-5]`) into individual numbers
4. Replaces `[N]` markers with `[[Source Title#Passage N]]` wikilinks
5. Writes a `reference` type note with resolved answer + sources table
6. Lists uncited sources separately

**Known limitation:** NotebookLM's `references[]` often covers only a few sources even when the answer synthesizes across all of them. The resolver warns about this and lists uncited sources in a separate section.

## Step 5: Verify

Open the Q&A note in Obsidian and check:
- [ ] Wikilinks render (not raw `[N]` markers)
- [ ] Clicking a source wikilink opens the correct source file at the passage
- [ ] `#Passage N` anchors scroll to the cited evidence in source files
- [ ] Sources Referenced section at bottom lists all cited sources
- [ ] Uncited Sources section lists sources without granular citations

## Multi-Turn Deep Dive Flow

For iterative Q&A sessions:

```
Turn 1: Ask broad question
  → Save qa-1.json, note conversation_id

Turn 2: Follow up on specifics
  → python3 ask_notebook.py --conversation-id {id} --question "..." > qa-2.json

Turn 3: Drill deeper
  → python3 ask_notebook.py --conversation-id {id} --question "..." > qa-3.json

Extract all passages at once:
  → python3 extract_passages.py --qa qa-1.json qa-2.json qa-3.json ...

Resolve into one conversation note:
  → python3 resolve_citations.py --qa qa-1.json ... --title "Session: {topic}"
```

Passages accumulate across turns (extract_passages is idempotent — skips existing passages). One reference note per conversation captures the full deep dive.

## Batch Mode

For multiple independent questions (no threading):

```bash
for q in "${questions[@]}"; do
    ~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/ask_notebook.py \
      --notebook-id {notebook-id} \
      --question "$q" > "/tmp/qa-${i}.json"
done

# Extract passages from all at once
~/projects/notebooklm-py/.venv/bin/python3 .claude/skills/notebooklm/scripts/extract_passages.py \
  --qa /tmp/qa-*.json \
  --sources "$SOURCES_FILE" \
  --slug {notebook-slug}
```

## Output

- Q&A reference note at `{vault-path}/{notebook-slug}/QA/{date} {title}.md`
- All `[N]` citations resolved to `[[Source Title#Passage N]]` wikilinks
- Source files enriched with `## Cited Passages` sections
- Uncited sources listed separately
- `conversation_id` in JSON output for follow-up questions
