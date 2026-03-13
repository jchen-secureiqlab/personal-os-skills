#!/usr/bin/env python3
"""Import NotebookLM sources into vault as notebook-source files.

Usage:
  python3 import_sources.py --notebook-id <id> --slug my-notebook --dashboard "Dashboard Title"
  python3 import_sources.py --notebook-id <id> --slug my-notebook --dashboard "Dashboard Title" \
      --vault-path 30_Sources/NotebookLM --dashboard-path Notes/Dashboards
  python3 import_sources.py --notebook-id <id> --slug my-notebook --dashboard "Dashboard Title" \
      --skip-guides

Fetches sources from the NotebookLM API and creates one .md file per source
with frontmatter + AI-generated source guide in the Obsidian vault.
"""
import argparse
import asyncio
import sys

from shared import (
    ensure_notebooklm_importable,
    markdown_heading_safe,
    retry_on_rate_limit,
    safe_filename,
    validate_slug,
    wikilink_safe,
    yaml_escape,
)

ensure_notebooklm_importable()

from pathlib import Path  # noqa: E402

from notebooklm import AuthError, NotebookLMClient  # noqa: E402

VAULT = Path.cwd()  # Expected to run from vault root

# Map SourceType enum values to our short source_type names
TYPE_MAP = {
    "youtube": "youtube",
    "web_page": "web",
    "pdf": "pdf",
    "pasted_text": "text",
    "google_docs": "gdocs",
    "google_slides": "gslides",
    "google_spreadsheet": "gsheets",
    "google_drive_audio": "audio",
    "google_drive_video": "video",
    "unknown": "unknown",
}


async def import_sources(args: argparse.Namespace) -> None:
    """Fetch sources from NotebookLM API and write vault markdown files."""
    try:
        async with await NotebookLMClient.from_storage() as client:
            sources = await retry_on_rate_limit(client.sources.list, args.notebook_id)
    except AuthError as e:
        print(f"ERROR: Authentication failed — {e}", file=sys.stderr)
        print("Run 'notebooklm login' to refresh credentials.", file=sys.stderr)
        sys.exit(1)

    if not sources:
        print("No sources found in notebook.")
        return

    # Build output paths
    vault_base = args.vault_path or "Notes/NotebookLM"
    dashboard_base = args.dashboard_path or "Notes/Dashboards"
    sources_dir = VAULT / vault_base / args.slug / "Sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = f"{dashboard_base}/{args.dashboard}"

    created = 0
    skipped = 0
    errors = 0

    async with await NotebookLMClient.from_storage() as client:
        for source in sources:
            title = (source.title or "").strip()
            source_id = source.id
            source_type = TYPE_MAP.get(str(source.kind), "web")
            url = source.url or ""
            date = source.created_at.strftime("%Y-%m-%d") if source.created_at else ""

            # Skip sources with garbage titles
            if title == "- YouTube" or len(title) < 3:
                print(f"  SKIP: '{title}' (bad title)")
                skipped += 1
                continue

            filename = safe_filename(title) + ".md"
            filepath = sources_dir / filename

            if filepath.exists():
                print(f"  EXISTS: {filename}")
                skipped += 1
                continue

            # Fetch guide if not skipped
            guide_text = ""
            keywords = []
            if not args.skip_guides:
                print(f"  Fetching guide: {title[:60]}...")
                try:
                    guide = await retry_on_rate_limit(
                        client.sources.get_guide, args.notebook_id, source_id
                    )
                    summary = guide.get("summary", "")
                    keywords = guide.get("keywords", [])
                    if summary:
                        guide_text = summary
                        if keywords:
                            guide_text += "\n\n### Topics\n\n" + ", ".join(keywords)
                        print(f"    OK: {len(summary)} chars, {len(keywords)} keywords")
                    else:
                        print("    WARN: no guide returned")
                except Exception as e:
                    print(f"    ERROR fetching guide: {e}", file=sys.stderr)
                    errors += 1

            # Build topics frontmatter
            topics_yaml = ""
            if keywords:
                safe_topics = [wikilink_safe(k) for k in keywords]
                topics_yaml = "topics:\n" + "\n".join(f'  - "[[{t}]]"' for t in safe_topics) + "\n"

            safe_source_id = yaml_escape(source_id)
            safe_notebook_id = yaml_escape(args.notebook_id)
            safe_url = yaml_escape(url)
            safe_title = markdown_heading_safe(title)

            content = f"""---
type: notebook-source
source_id: "{safe_source_id}"
notebook_id: "{safe_notebook_id}"
url: "{safe_url}"
source_type: {source_type}
status: active
date: {date}
{topics_yaml}related:
  - "[[{dashboard_path}]]"
---

# {safe_title}

## Source Guide

{guide_text}
"""

            filepath.write_text(content)
            print(f"  CREATED: {filename}")
            created += 1

    print(f"\nDone: {created} created, {skipped} skipped, {errors} errors")


def main():
    parser = argparse.ArgumentParser(description="Import NotebookLM sources into vault")
    parser.add_argument("--notebook-id", required=True, help="NotebookLM notebook ID")
    parser.add_argument("--slug", required=True, help="Notebook slug (kebab-case folder name)")
    parser.add_argument("--dashboard", required=True, help="Dashboard title for related links")
    parser.add_argument("--skip-guides", action="store_true", help="Skip fetching AI source guides")
    parser.add_argument(
        "--vault-path",
        default=None,
        help="Vault subfolder for sources (default: Notes/NotebookLM)",
    )
    parser.add_argument(
        "--dashboard-path",
        default=None,
        help="Vault subfolder for dashboards (default: Notes/Dashboards)",
    )
    args = parser.parse_args()
    validate_slug(args.slug)

    asyncio.run(import_sources(args))


if __name__ == "__main__":
    main()
