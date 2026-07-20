import ipaddress
import re
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

import fitz  # pymupdf

_JINA_PREFIX = "https://r.jina.ai/"


def _is_public_http_url(url: str) -> bool:
    """Guard against SSRF: only allow public http(s) targets, reject other
    schemes and obvious internal hosts (localhost / private / link-local IPs)."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True  # a hostname, not a literal IP — allowed
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)


def extract_pdf_text(path: str) -> str:
    doc = fitz.open(path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _jina_get(target: str) -> str:
    req = urllib.request.Request(target, headers={"User-Agent": "FragilityGraph/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (fixed jina host)
        return resp.read().decode("utf-8", errors="replace")


def fetch_url_text(url: str, *, max_chars: int | None = None, fetcher=None) -> str:
    """Read a web page (e.g. an SEC filing) as clean text via the Jina Reader.

    Jina (r.jina.ai) fetches and renders the page to markdown, sidestepping SEC's
    403-to-generic-fetchers and HTML noise. The complete result is returned by
    default; callers can set `max_chars` when they explicitly need a bounded
    response. `fetcher` is injectable for tests (no network)."""
    if not _is_public_http_url(url):
        raise ValueError("only public http(s) URLs are allowed")
    target = _JINA_PREFIX + url
    get = fetcher or _jina_get
    text = get(target)
    return text if max_chars is None else text[:max_chars]


@dataclass(frozen=True)
class Passage:
    text: str
    char_start: int
    char_end: int


def split_passages(text: str) -> list[Passage]:
    passages: list[Passage] = []
    pos = 0
    for block in re.split(r"\n\s*\n", text):
        start = text.index(block, pos)
        pos = start + len(block)
        stripped = block.strip()
        if not stripped:
            continue
        lead = len(block) - len(block.lstrip())
        char_start = start + lead
        char_end = char_start + len(stripped)
        passages.append(Passage(text=stripped, char_start=char_start, char_end=char_end))
    return passages


def chunk_document(text: str, *, max_chars: int = 30_000) -> list[str]:
    """Pack document paragraphs into bounded chunks with light overlap."""
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    chunks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            chunks.append("\n\n".join(current))

    for passage in split_passages(text):
        if len(passage.text) > max_chars:
            flush()
            current = []
            chunks.extend(
                passage.text[start:start + max_chars]
                for start in range(0, len(passage.text), max_chars)
            )
            continue

        candidate = "\n\n".join([*current, passage.text])
        if current and len(candidate) > max_chars:
            previous = current[-1]
            flush()
            current = [previous, passage.text]
            if len("\n\n".join(current)) > max_chars:
                current = [passage.text]
        else:
            current.append(passage.text)

    flush()
    return chunks
