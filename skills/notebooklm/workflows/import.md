# Import Notebook Workflow

Import all sources from a NotebookLM notebook into the vault as linked `notebook-source` files with AI-generated guides, plus a dashboard.

## Inputs

- **notebook-id**: NotebookLM notebook ID (required)
- **notebook-slug**: short kebab-case name for the notebook (e.g. `obsidian-x-claude-code`)
- **dashboard-title**: human-readable title for the dashboard (e.g. `Obsidian x Claude Code Research`)
- **vault-path**: vault subfolder for sources (optional, default: `Notes/NotebookLM`)
- **dashboard-path**: vault subfolder for dashboards (optional, default: `Notes/Dashboards`)

If user doesn't specify notebook-id or slug, derive from `notebooklm status` output.

**Vault layout:** The default layout is `Notes/NotebookLM/{slug}/Sources/`. For PARA-style vaults, pass `--vault-path 30_Sources/NotebookLM` to write to `30_Sources/NotebookLM/{slug}/Sources/` instead.

## Step 1: Verify Auth

```bash
notebooklm status
```

If auth error: run `notebooklm login` to re-authenticate.

## Step 2: Get Notebook Info

```bash
notebooklm status
# Note the notebook_id and title
```

## Step 3: Create Folder Structure

```bash
VAULT_PATH="${vault-path:-Notes/NotebookLM}"
mkdir -p "$VAULT_PATH/{notebook-slug}/Sources"
mkdir -p "$VAULT_PATH/{notebook-slug}/QA"
```

## Step 4: Create Source Files with Guides

Run the import script — it fetches sources from the API and creates vault files with AI-generated guides:

```bash
python3 .claude/skills/notebooklm/scripts/import_sources.py \
  --notebook-id {notebook-id} \
  --slug {notebook-slug} \
  --dashboard "{dashboard-title}" \
  --vault-path "{vault-path}" \
  --dashboard-path "{dashboard-path}"
```

This:
1. Fetches all sources from the notebook via the Python API
2. Creates one `.md` file per source with frontmatter, topic wikilinks, and `related` linking to dashboard
3. Fetches AI-generated source guides with retry on rate limiting
4. Skips sources with bad titles (< 3 chars, "- YouTube")
5. Skips existing files (idempotent — safe to re-run)

**Note:** Guide fetching is sequential (one API call per source with rate limit retry). For 20 sources, expect ~2-3 minutes.

Omit `--vault-path` and `--dashboard-path` to use defaults (`Notes/NotebookLM` and `Notes/Dashboards`).

To skip guide fetching (faster but no AI summaries):

```bash
python3 .claude/skills/notebooklm/scripts/import_sources.py \
  --notebook-id {notebook-id} \
  --slug {notebook-slug} \
  --dashboard "{dashboard-title}" \
  --skip-guides
```

## Step 5: Create Dashboard

Create `{dashboard-path}/{dashboard-title}.md` using the dashboard template from `templates/dashboard.md`.

Replace `{notebook-slug}` and vault path references in the Dataview queries.

## Step 6: Verify

```bash
# Check source count
ls "$VAULT_PATH/{notebook-slug}/Sources/" | wc -l
```

Open the dashboard in Obsidian and verify Dataview queries render.

## Output

- `N` source files in `{vault-path}/{notebook-slug}/Sources/`
- Dashboard at `{dashboard-path}/{dashboard-title}.md`
- Empty `QA/` folder ready for ask workflow
