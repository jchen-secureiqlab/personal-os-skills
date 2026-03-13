#!/usr/bin/env python3
"""Import pipeline research output into NotebookLM.

Usage:
  # Into existing notebook
  python3 pipeline_bridge.py --notebook-id <id> /path/to/output/YYYY-MM-DD-run-NNN/

  # Create new notebook
  python3 pipeline_bridge.py --create "AI Agent Security" /path/to/output/YYYY-MM-DD-run-NNN/

Imports research-only material from a pipeline run:
  - 02b-verified-research.md (preferred) or 02-research.md (fallback)
  - URL import from 01-discover.json is deferred (schema not yet defined)

Writes bridge-manifest.json for idempotent re-runs.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from shared import ensure_notebooklm_importable, retry_on_rate_limit

ensure_notebooklm_importable()

from notebooklm import AuthError, NotebookLMClient  # noqa: E402


def find_research_file(run_dir: Path) -> tuple[Path, bool] | None:
    """Find the best research file in the run directory.

    Returns (path, is_verified) or None if no research file exists.
    Prefers verified research over unverified.
    """
    verified = run_dir / "02b-verified-research.md"
    if verified.exists():
        return verified, True

    unverified = run_dir / "02-research.md"
    if unverified.exists():
        return unverified, False

    return None


def load_manifest(run_dir: Path) -> dict:
    """Load bridge-manifest.json if it exists."""
    manifest_path = run_dir / "bridge-manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {}


def save_manifest(run_dir: Path, manifest: dict) -> None:
    """Write bridge-manifest.json to the run directory."""
    manifest_path = run_dir / "bridge-manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def extract_topic(run_dir: Path) -> str:
    """Try to extract the topic from 01-discover.json."""
    discover = run_dir / "01-discover.json"
    if discover.exists():
        try:
            with open(discover) as f:
                data = json.load(f)
            return data.get("topic", data.get("title", run_dir.name))
        except (json.JSONDecodeError, KeyError):
            pass
    return run_dir.name


async def bridge_import(args: argparse.Namespace) -> None:
    """Import pipeline research into NotebookLM."""
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Find research file
    research_result = find_research_file(run_dir)
    if research_result is None:
        print(
            f"WARNING: No research files found in {run_dir} "
            "(expected 02b-verified-research.md or 02-research.md)",
            file=sys.stderr,
        )
        sys.exit(0)

    research_path, is_verified = research_result
    topic = extract_topic(run_dir)

    # Check manifest for idempotency
    manifest = load_manifest(run_dir)
    imported_titles = set(manifest.get("imported_sources", []))

    suffix = " (verified)" if is_verified else ""
    source_title = f"Research: {topic}{suffix}"

    if source_title in imported_titles:
        print(f"  SKIP: '{source_title}' (already imported per manifest)")
        print("\nDone: 0 imported, 1 skipped")
        return

    # URL import deferred
    print("  INFO: URL import from 01-discover.json skipped (schema not yet defined)")

    # Connect to NotebookLM
    try:
        async with await NotebookLMClient.from_storage() as client:
            # Create or target notebook
            if args.create:
                notebook = await retry_on_rate_limit(client.notebooks.create, args.create)
                notebook_id = notebook.id
                print(f"  CREATED notebook: {args.create} ({notebook_id})")
            else:
                notebook_id = args.notebook_id

            # Import research as text source
            research_content = research_path.read_text()
            print(f"  Importing: {source_title} ({len(research_content)} chars)...")

            source = await retry_on_rate_limit(
                client.sources.add_text,
                notebook_id,
                source_title,
                research_content,
                wait=True,
            )
            print(f"  IMPORTED: {source_title} (source_id: {source.id})")

    except AuthError as e:
        print(f"ERROR: Authentication failed — {e}", file=sys.stderr)
        print("Run 'notebooklm login' to refresh credentials.", file=sys.stderr)
        sys.exit(1)

    # Update manifest
    manifest["notebook_id"] = notebook_id
    manifest.setdefault("imported_sources", []).append(source_title)
    manifest["last_import"] = datetime.now(timezone.utc).isoformat()
    save_manifest(run_dir, manifest)

    print(f"\nDone: 1 imported, 0 skipped")
    print(f"Manifest written: {run_dir / 'bridge-manifest.json'}")


def main():
    parser = argparse.ArgumentParser(description="Import pipeline research into NotebookLM")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--notebook-id", help="Import into existing notebook")
    group.add_argument("--create", help="Create new notebook with this title")
    parser.add_argument("run_dir", help="Pipeline run directory (output/YYYY-MM-DD-run-NNN/)")
    args = parser.parse_args()

    asyncio.run(bridge_import(args))


if __name__ == "__main__":
    main()
