"""Shared utilities for NotebookLM skill scripts.

Provides input validation, filename sanitization, injection escaping,
and async API helpers used across all NotebookLM skill scripts.
"""
import asyncio
import os
import re
import sys


# --- Slug validation ---

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_SLUG_MAX = 80


def validate_slug(slug: str) -> None:
    """Validate that slug is kebab-case: [a-z0-9-], max 80 chars.

    Exits with an error message if invalid. Call immediately after argparse.

    >>> validate_slug("my-notebook")
    >>> validate_slug("a")
    >>> import subprocess, sys
    >>> r = subprocess.run([sys.executable, "-c",
    ...     "from shared import validate_slug; validate_slug('../../etc')"],
    ...     capture_output=True, text=True, cwd=__import__('pathlib').Path(__file__).parent)
    >>> r.returncode != 0
    True
    """
    if not slug or len(slug) > _SLUG_MAX or not _SLUG_RE.match(slug):
        print(
            f"ERROR: invalid slug {slug!r} — must be kebab-case "
            f"([a-z0-9-], max {_SLUG_MAX} chars, no leading/trailing dash)",
            file=sys.stderr,
        )
        sys.exit(1)


# --- Filename sanitization ---

_UNSAFE_CHARS_RE = re.compile(r'[/:*?"<>|\\]')
_DOTDOT_RE = re.compile(r"\.\.")
_WHITESPACE_RE = re.compile(r"\s+")
_LEADING_DOTS_DASHES_RE = re.compile(r"^[.\-]+")
_MAX_FILENAME = 120


def safe_filename(title: str) -> str:
    """Make title safe for filesystem use.

    - Strips unsafe characters (including backslash)
    - Collapses '..' to '_'
    - Strips leading dots and dashes
    - Collapses whitespace
    - Truncates to 120 chars
    - Falls back to 'untitled' if empty after sanitization

    >>> safe_filename('../../etc/passwd')
    '_-_-etc-passwd'
    >>> safe_filename('foo\\\\bar')
    'foo-bar'
    >>> safe_filename('...')
    '_.'
    >>> safe_filename('')
    'untitled'
    >>> safe_filename('  ')
    'untitled'
    >>> safe_filename('---')
    'untitled'
    >>> safe_filename('normal title')
    'normal title'
    >>> safe_filename('a' * 200)[:120] == 'a' * 120
    True
    """
    title = _UNSAFE_CHARS_RE.sub("-", title)
    title = _DOTDOT_RE.sub("_", title)
    title = _WHITESPACE_RE.sub(" ", title).strip()
    title = _LEADING_DOTS_DASHES_RE.sub("", title)
    if len(title) > _MAX_FILENAME:
        title = title[:_MAX_FILENAME].rstrip(" -")
    if not title:
        title = "untitled"
    return title


# --- YAML / Markdown injection escaping ---


def yaml_escape(val: str) -> str:
    """Escape a string for use in YAML double-quoted values.

    Handles backslashes, double quotes, and newlines.

    >>> yaml_escape('normal')
    'normal'
    >>> yaml_escape('has "quotes"')
    'has \\\\"quotes\\\\"'
    >>> yaml_escape('line1\\nline2')
    'line1\\\\nline2'
    >>> yaml_escape('back\\\\slash')
    'back\\\\\\\\slash'
    """
    val = val.replace("\\", "\\\\")
    val = val.replace('"', '\\"')
    val = val.replace("\n", "\\n")
    val = val.replace("\r", "\\r")
    return val


def markdown_heading_safe(title: str) -> str:
    """Strip characters that could break or inject into Markdown headings.

    Removes newlines and carriage returns to prevent heading injection.

    >>> markdown_heading_safe('Normal Title')
    'Normal Title'
    >>> markdown_heading_safe('Title\\n## Injected Heading')
    'Title ## Injected Heading'
    >>> markdown_heading_safe('Title\\r\\nInjected')
    'Title Injected'
    """
    return title.replace("\r", "").replace("\n", " ")


def wikilink_safe(text: str) -> str:
    """Strip characters that could break or inject into Obsidian [[wikilinks]].

    Removes ]], [[, and | to prevent wikilink injection.

    >>> wikilink_safe('Normal Topic')
    'Normal Topic'
    >>> wikilink_safe('Topic [[injected]]')
    'Topic injected'
    >>> wikilink_safe('Topic|alias')
    'Topicalias'
    """
    text = text.replace("]]", "")
    text = text.replace("[[", "")
    text = text.replace("|", "")
    return text


# --- notebooklm-py import guard ---

_NOTEBOOKLM_PY_SRC = os.path.expanduser("~/projects/notebooklm-py/src")


def ensure_notebooklm_importable():
    """Add notebooklm-py to sys.path if not already importable.

    Call at the top of any script that uses the NotebookLMClient API.
    Exits with a clear error if the package cannot be found.
    """
    try:
        import notebooklm  # noqa: F401
    except ImportError:
        if os.path.isdir(_NOTEBOOKLM_PY_SRC):
            sys.path.insert(0, _NOTEBOOKLM_PY_SRC)
            try:
                import notebooklm  # noqa: F401
            except ImportError:
                print(
                    "ERROR: notebooklm-py found at "
                    f"{_NOTEBOOKLM_PY_SRC} but failed to import.",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                f"ERROR: notebooklm-py not found at {_NOTEBOOKLM_PY_SRC}",
                file=sys.stderr,
            )
            print(
                "Clone it or update _NOTEBOOKLM_PY_SRC in shared.py.",
                file=sys.stderr,
            )
            sys.exit(1)


# --- Async API helpers ---


async def retry_on_rate_limit(coro_fn, *args, max_retries=3, **kwargs):
    """Retry an async callable on RateLimitError with backoff.

    Uses retry_after from the error when available, otherwise waits 60s.
    """
    from notebooklm import RateLimitError

    for attempt in range(max_retries + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except RateLimitError as e:
            if attempt == max_retries:
                raise
            wait = e.retry_after or 60
            print(
                f"  Rate limited. Waiting {wait}s "
                f"(attempt {attempt + 1}/{max_retries})...",
                file=sys.stderr,
            )
            await asyncio.sleep(wait)


if __name__ == "__main__":
    import doctest

    results = doctest.testmod(verbose=True)
    sys.exit(0 if results.failed == 0 else 1)
