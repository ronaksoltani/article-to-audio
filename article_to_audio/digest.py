"""Article extraction, sentence-safe chunking, and MP3 generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
import trafilatura
from gtts import gTTS
from pydub import AudioSegment

USER_AGENT = "ArticleToAudioDigest/1.0 (educational project)"


@dataclass(frozen=True)
class Article:
    title: str
    text: str
    url: str


def fetch_article(url: str, timeout: float = 20) -> Article:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a complete http or https article URL.")
    response = requests.get(url, timeout=(5, timeout), headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    if len(response.content) > 12_000_000:
        raise ValueError("The page is larger than the 12 MB safety limit.")
    html = response.text
    text = trafilatura.extract(
        html,
        output_format="txt",
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if not text or not text.strip():
        raise ValueError("Could not extract a readable article body from this page.")
    metadata = trafilatura.extract_metadata(html)
    title = metadata.title.strip() if metadata and metadata.title else parsed.netloc
    return Article(title=title, text=text.strip(), url=url)


def chunk_text(text: str, maximum: int) -> list[str]:
    if maximum < 100:
        raise ValueError("Chunk size must be at least 100 characters.")
    words = re.findall(r"\S+", text)
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for word in words:
        if len(word) > maximum:
            if current:
                chunks.append(" ".join(current))
                current, size = [], 0
            chunks.extend(word[index:index + maximum] for index in range(0, len(word), maximum))
            continue
        added = len(word) + (1 if current else 0)
        if current and size + added > maximum:
            chunks.append(" ".join(current))
            current, size = [word], len(word)
        else:
            current.append(word)
            size += added
    if current:
        chunks.append(" ".join(current))
    return chunks


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return (slug[:64].strip("-") or "article")


def create_mp3(article: Article, output_dir: Path, language: str, max_chars: int) -> Path:
    chunks = chunk_text(article.text, max_chars)
    combined = AudioSegment.empty()
    for index, text in enumerate(chunks, start=1):
        buffer = BytesIO()
        gTTS(text=text, lang=language, slow=False).write_to_fp(buffer)
        buffer.seek(0)
        combined += AudioSegment.from_file(buffer, format="mp3")
        print(f"Generated audio segment {index}/{len(chunks)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().astimezone().strftime("%Y-%m-%d")
    destination = output_dir / f"{date}-{slugify(article.title)}.mp3"
    temporary = destination.with_name(destination.stem + ".tmp.mp3")
    combined.export(temporary, format="mp3", bitrate="128k")
    temporary.replace(destination)
    return destination
