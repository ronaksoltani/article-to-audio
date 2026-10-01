"""Command-line interface for article audio generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .digest import create_mp3, fetch_article, slugify


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Extract an article and create a spoken MP3.")
    result.add_argument("url", help="Public article URL")
    result.add_argument("--language", default="en", help="gTTS language code (default: en)")
    result.add_argument("--output-dir", type=Path, default=Path("audio"))
    result.add_argument("--max-chars", type=int, default=2800, help="Maximum text size per speech segment")
    result.add_argument("--text-copy", action="store_true", help="Save the extracted plain text beside the MP3")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        article = fetch_article(args.url)
        output_dir = args.output_dir.expanduser().resolve()
        if args.text_copy:
            output_dir.mkdir(parents=True, exist_ok=True)
            text_path = output_dir / f"{slugify(article.title)}.txt"
            text_path.write_text(article.text + "\n", encoding="utf-8")
            print(f"Text saved to {text_path}")
        audio_path = create_mp3(article, output_dir, args.language, args.max_chars)
    except (ValueError, OSError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Title: {article.title}")
    print(f"Audio: {audio_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
