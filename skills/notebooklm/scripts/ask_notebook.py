#!/usr/bin/env python3
"""Ask a NotebookLM notebook a question with conversation threading.

Usage:
  # New conversation
  python3 ask_notebook.py --notebook-id <id> --question "What are the key findings?"

  # Follow-up (uses conversation_id from previous output)
  python3 ask_notebook.py --notebook-id <id> --question "Tell me more about finding 3" \
      --conversation-id <conv-id>

  # With chat mode
  python3 ask_notebook.py --notebook-id <id> --question "Explain transformers" \
      --mode learning-guide

  # With custom persona
  python3 ask_notebook.py --notebook-id <id> --question "Summarize" \
      --persona "You are a security analyst. Focus on risks and mitigations."

Outputs JSON to stdout with answer, conversation_id, turn_number, and references.
"""
import argparse
import asyncio
import json
import sys

from shared import ensure_notebooklm_importable, retry_on_rate_limit

ensure_notebooklm_importable()

from notebooklm import AuthError, NotebookLMClient  # noqa: E402

# Map CLI mode names to ChatMode enum values
MODE_MAP = {
    "default": "DEFAULT",
    "learning-guide": "LEARNING_GUIDE",
    "concise": "CONCISE",
    "detailed": "DETAILED",
}

# Map CLI response length names
LENGTH_MAP = {
    "shorter": "SHORTER",
    "default": "DEFAULT",
    "longer": "LONGER",
}


async def ask_notebook(args: argparse.Namespace) -> None:
    """Ask a question and output JSON result."""
    try:
        async with await NotebookLMClient.from_storage() as client:
            # Configure chat mode/persona if specified
            if args.mode or args.persona or args.response_length:
                from notebooklm.rpc.types import ChatGoal, ChatResponseLength

                goal = None
                custom_prompt = None
                response_length = None

                if args.persona:
                    goal = ChatGoal.CUSTOM
                    custom_prompt = args.persona
                elif args.mode:
                    mode_key = MODE_MAP.get(args.mode)
                    if mode_key == "LEARNING_GUIDE":
                        goal = ChatGoal.LEARNING_GUIDE
                    else:
                        goal = ChatGoal.DEFAULT

                if args.response_length:
                    length_key = LENGTH_MAP.get(args.response_length, "DEFAULT")
                    response_length = ChatResponseLength[length_key]
                elif args.mode:
                    # Set response length based on mode
                    if args.mode == "concise":
                        response_length = ChatResponseLength.SHORTER
                    elif args.mode in ("detailed", "learning-guide"):
                        response_length = ChatResponseLength.LONGER

                await retry_on_rate_limit(
                    client.chat.configure,
                    args.notebook_id,
                    goal=goal,
                    response_length=response_length,
                    custom_prompt=custom_prompt,
                )

            # Ask the question
            result = await retry_on_rate_limit(
                client.chat.ask,
                args.notebook_id,
                args.question,
                conversation_id=args.conversation_id,
            )

    except AuthError as e:
        print(f"ERROR: Authentication failed — {e}", file=sys.stderr)
        print("Run 'notebooklm login' to refresh credentials.", file=sys.stderr)
        sys.exit(1)

    # Serialize to JSON
    output = {
        "answer": result.answer,
        "conversation_id": result.conversation_id,
        "turn_number": result.turn_number,
        "is_follow_up": result.is_follow_up,
        "references": [
            {
                "source_id": ref.source_id,
                "cited_text": ref.cited_text or "",
                "citation_number": ref.citation_number,
            }
            for ref in result.references
        ],
    }

    json.dump(output, sys.stdout, indent=2)
    print(file=sys.stderr)  # newline for stderr diagnostics
    print(
        f"Turn {result.turn_number}: {len(result.answer)} chars, "
        f"{len(result.references)} references, "
        f"conversation_id={result.conversation_id}",
        file=sys.stderr,
    )


def main():
    parser = argparse.ArgumentParser(description="Ask a NotebookLM notebook a question")
    parser.add_argument("--notebook-id", required=True, help="NotebookLM notebook ID")
    parser.add_argument("--question", required=True, help="Question to ask")
    parser.add_argument(
        "--conversation-id",
        default=None,
        help="Conversation ID for follow-up questions (from previous output)",
    )
    parser.add_argument(
        "--mode",
        choices=["default", "learning-guide", "concise", "detailed"],
        default=None,
        help="Chat mode preset",
    )
    parser.add_argument(
        "--persona",
        default=None,
        help="Custom persona prompt (overrides --mode)",
    )
    parser.add_argument(
        "--response-length",
        choices=["shorter", "default", "longer"],
        default=None,
        help="Response length preference",
    )
    args = parser.parse_args()

    asyncio.run(ask_notebook(args))


if __name__ == "__main__":
    main()
