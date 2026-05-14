import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


DOMAIN_LIMIT = 2
TRACKING_PARAMS_PREFIXES = ("utm_",)
TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "spm",
    "ved",
}

TRUSTED_DOMAIN_HINTS = (
    ".edu",
    ".gov",
    ".org",
    "wikipedia.org",
    "arxiv.org",
    "github.com",
    "docs.",
)

SOURCE_TYPES = {
    "official": "官方/文档",
    "academic": "学术资料",
    "encyclopedia": "百科资料",
    "code": "代码仓库",
    "community": "社区讨论",
    "news": "新闻媒体",
    "blog": "博客文章",
    "general": "普通网页",
}


def clean_text(text: str) -> str:
    """Normalize source text before chunking and prompt construction."""
    text = re.sub(r"!\[[^\]]*]\([^)]+\)", "", text)
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def canonicalize_url(url: str) -> str:
    """Remove fragments and tracking parameters for stable source deduplication."""
    if not url:
        return ""

    parsed = urlparse(url.strip())
    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower in TRACKING_PARAMS:
            continue
        if any(key_lower.startswith(prefix) for prefix in TRACKING_PARAMS_PREFIXES):
            continue
        query_pairs.append((key, value))

    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    return urlunparse((
        parsed.scheme.lower() or "https",
        netloc,
        parsed.path.rstrip("/") or "/",
        "",
        urlencode(query_pairs),
        "",
    ))


def _query_terms(query: str) -> set[str]:
    query = query.lower()
    return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", query))


def _overlap_score(query: str, text: str) -> float:
    terms = _query_terms(query)
    if not terms:
        return 0.0
    text_lower = text.lower()
    matched = sum(1 for term in terms if term in text_lower)
    return matched / len(terms)


def _domain_score(url: str) -> float:
    host = urlparse(url).netloc.lower()
    source_type = classify_source(url)
    if source_type in {"official", "academic"}:
        return 1.0
    if any(hint in host for hint in TRUSTED_DOMAIN_HINTS):
        return 0.9
    if source_type in {"encyclopedia", "code"}:
        return 0.8
    if source_type in {"news", "community"}:
        return 0.6
    return 0.5 if host else 0.0


def classify_source(url: str) -> str:
    """Classify source type from domain/path for explainable ranking."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if not host:
        return "general"
    if host.endswith(".edu") or host.endswith(".edu.cn") or "arxiv.org" in host:
        return "academic"
    if host.endswith(".gov") or host.endswith(".gov.cn"):
        return "official"
    if (
        host.startswith("docs.")
        or ".docs." in host
        or "developer." in host
        or "learn.microsoft.com" in host
        or "docs.python.org" in host
        or "/docs" in path
        or "/documentation" in path
    ):
        return "official"
    if "wikipedia.org" in host or "baike.baidu.com" in host:
        return "encyclopedia"
    if "github.com" in host or "gitlab.com" in host:
        return "code"
    if any(domain in host for domain in ("stackoverflow.com", "zhihu.com", "reddit.com", "segmentfault.com")):
        return "community"
    if any(domain in host for domain in ("news", "36kr.com", "thepaper.cn", "cnn.com", "bbc.com")):
        return "news"
    if any(token in host or token in path for token in ("blog", "medium.com", "dev.to")):
        return "blog"
    return "general"


def _quality_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def score_source(query: str, source: dict) -> float:
    """Blend search relevance, text richness, title match, and domain signal."""
    tavily_score = float(source.get("score") or 0)
    tavily_score = max(0.0, min(tavily_score, 1.0))
    content = clean_text(source.get("content") or source.get("snippet") or "")
    title = source.get("title") or ""

    length_score = min(len(content) / 800, 1.0)
    title_overlap = _overlap_score(query, title)
    content_overlap = _overlap_score(query, content)
    source_type = classify_source(source.get("url", ""))
    domain_score = _domain_score(source.get("url", ""))
    type_bonus = 0.05 if source_type in {"official", "academic", "encyclopedia", "code"} else 0.0

    score = (
        tavily_score * 0.45
        + length_score * 0.20
        + title_overlap * 0.15
        + content_overlap * 0.10
        + domain_score * 0.10
        + type_bonus
    )
    return round(max(0.0, min(score, 1.0)), 4)


def _content_fingerprint(text: str) -> str:
    normalized = clean_text(text).lower()[:600]
    return hashlib.md5(normalized.encode()).hexdigest()


def process_sources(query: str, sources: list[dict], limit: int = 8) -> list[dict]:
    """Clean, deduplicate, and quality-rank raw search sources."""
    processed = []
    seen_urls: set[str] = set()
    seen_content: set[str] = set()

    for source in sources:
        content = clean_text(source.get("content") or source.get("snippet") or "")
        snippet = clean_text(source.get("snippet") or content)
        if len(content) < 20 and len(snippet) < 20:
            continue

        canonical_url = canonicalize_url(source.get("url", ""))
        if canonical_url and canonical_url in seen_urls:
            continue

        fingerprint = _content_fingerprint(content or snippet)
        if fingerprint in seen_content:
            continue

        normalized = {
            **source,
            "url": canonical_url or source.get("url", ""),
            "snippet": snippet[:500],
            "content": content,
        }
        source_type = classify_source(normalized["url"])
        quality_score = score_source(query, normalized)
        normalized["quality_score"] = quality_score
        normalized["quality_label"] = _quality_label(quality_score)
        normalized["source_type"] = source_type
        normalized["source_type_label"] = SOURCE_TYPES[source_type]

        seen_urls.add(normalized["url"])
        seen_content.add(fingerprint)
        processed.append(normalized)

    processed.sort(
        key=lambda item: (
            item.get("quality_score", 0),
            item.get("score", 0),
        ),
        reverse=True,
    )

    diversified = []
    domain_counts: dict[str, int] = {}
    for item in processed:
        host = urlparse(item.get("url", "")).netloc
        if host and domain_counts.get(host, 0) >= DOMAIN_LIMIT:
            continue
        if host:
            domain_counts[host] = domain_counts.get(host, 0) + 1
        diversified.append(item)
        if len(diversified) >= limit:
            break

    return diversified
