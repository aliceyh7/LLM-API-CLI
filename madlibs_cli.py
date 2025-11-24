#!/usr/bin/env python3
"""
Generate a short Mad Libs game by asking Gemini to design a fresh template.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Blank:
    key: str
    prompt: str


@dataclass(frozen=True)
class StoryTemplate:
    title: str
    blanks: List[Blank]
    skeleton: str

    def build(self, answers: Dict[str, str]) -> str:
        return self.skeleton.format(**answers)


def get_client():
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise SystemExit(
            "Missing dependency 'google-genai'. Install it with 'pip install google-genai'."
        ) from exc
    return genai.Client()


def enforce_blank_range(value: str) -> int:
    count = int(value)
    if not 8 <= count <= 10:
        raise argparse.ArgumentTypeError("Blank count must be between 8 and 10.")
    return count


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        for chunk in parts:
            chunk = chunk.strip()
            if not chunk or chunk.lower() == "json":
                continue
            return chunk
    return cleaned


def parse_template_payload(payload: str) -> StoryTemplate:
    try:
        as_dict = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini response was not valid JSON.") from exc

    try:
        blanks_data = as_dict["blanks"]
        blanks = [Blank(key=item["key"], prompt=item["prompt"]) for item in blanks_data]
        template = StoryTemplate(
            title=as_dict["title"],
            blanks=blanks,
            skeleton=as_dict["skeleton"],
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("Gemini response JSON missed required fields.") from exc

    if not (8 <= len(template.blanks) <= 10):
        raise ValueError("Template must contain between 8 and 10 blanks.")
    return template


def build_template_prompt(blank_count: int, theme: str | None) -> str:
    theme_clause = theme or "surprise me with any playful theme"
    return textwrap.dedent(
        f"""
        You are designing a Mad Libs style word game.
        Produce a single JSON object with the following shape:
        {{
          "title": "<short descriptive title>",
          "blanks": [
            {{"key": "snake_case_identifier", "prompt": "Friendly input prompt"}},
            ...
          ],
          "skeleton": "Story text containing the placeholders like {{snake_case_identifier}}"
        }}

        Requirements:
        - Provide exactly {blank_count} blank entries.
        - Prompts should ask for varied parts of speech (nouns, adjectives, verbs, etc.).
        - The skeleton must stay between 120 and 200 words, upbeat, and themed around: {theme_clause}.
        - Use each placeholder exactly once and match the keys in the blanks list.
        - Return only raw JSON (no Markdown fences, code blocks, or commentary).
        """
    ).strip()


def request_template(client, blank_count: int, theme: str | None, model: str) -> StoryTemplate:
    prompt = build_template_prompt(blank_count, theme)
    response = client.models.generate_content(model=model, contents=prompt)
    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    payload = strip_code_fence(response.text)
    return parse_template_payload(payload)


def prompt_for_words(blanks: List[Blank]) -> Dict[str, str]:
    answers: Dict[str, str] = {}
    for blank in blanks:
        user_input = input(f"{blank.prompt.strip()} ").strip()
        answers[blank.key] = user_input
    return answers


def build_story(template: StoryTemplate) -> str:
    answers = prompt_for_words(template.blanks)
    try:
        return template.build(answers)
    except KeyError as exc:
        raise RuntimeError(f"Missing answer for placeholder: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLI Mad Libs powered by Gemini. Generates a template with 8-10 blanks."
    )
    parser.add_argument(
        "--blanks",
        type=enforce_blank_range,
        default=9,
        help="Number of blanks to request from Gemini (between 8 and 10).",
    )
    parser.add_argument(
        "--theme",
        help="Optional theme suggestion for the story (e.g., 'haunted spaceship').",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model to use (default: gemini-2.5-flash).",
    )
    parser.add_argument(
        "--show-template",
        action="store_true",
        help="Print the raw template JSON before playing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = get_client()
    template = request_template(client, args.blanks, args.theme, args.model)

    if args.show_template:
        dump = {
            "title": template.title,
            "blanks": [{"key": blank.key, "prompt": blank.prompt} for blank in template.blanks],
            "skeleton": template.skeleton,
        }
        print(json.dumps(dump, indent=2))

    print(f"\n🎲 Title: {template.title}\n")
    story = build_story(template)
    print("\nHere is your completed Mad Lib:\n")
    print(story)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nGame cancelled by user.")

