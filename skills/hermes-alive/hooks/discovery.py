"""DiscoveryEngine for Hermes Alive — finds interesting content from external
sources (arXiv, GitHub trending, HN) and local sources (TODO/FIXME, git log,
error logs, recent files).

Usage:
    engine = DiscoveryEngine()
    results = await engine.collect()
    print(results)

Design:
- All discovery happens asynchronously (aiohttp for external, subprocess for local)
- Error resilience: if any source fails, continue with others. Log errors, don't crash.
- Rate limiting: discovery runs at most once per configured interval
- Caching: results cached between discovery runs
- Non-blocking: discovery is async but should not block message sending
"""

from __future__ import annotations

# Marker: RICH_CONTENT_IMAGE_SOURCE_V1

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore[assignment]

DISCOVERY_INTERVAL_ENV = "HERMES_PROACTIVE_DISCOVERY_INTERVAL_SECONDS"
DEFAULT_DISCOVERY_INTERVAL = 86400  # 24 hours

HOME_DIR = os.path.expanduser("~")
DENIED_PATTERNS = (
    ".env", "auth.json", "storage_state.json", "cookie", "cookies",
    "token", "secret", "credential", "credentials", ".tar.gz", ".zip",
    "/private/", "/uploads/",
)

def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}

def _safe_work_dir(raw: str) -> str:
    if not raw:
        return ""
    if not _truthy_env("HERMES_DISCOVERY_LOCAL_ENABLED", "false"):
        return ""
    real = os.path.realpath(raw)
    allowed_raw = os.getenv("HERMES_DISCOVERY_ALLOWED_ROOTS", "")
    allowed = [os.path.realpath(p.strip()) for p in allowed_raw.split(":") if p.strip()]
    if not allowed:
        return ""
    if not any(real == root or real.startswith(root + os.sep) for root in allowed):
        logger.warning("LocalDiscovery denied unsafe work dir: %s", real)
        return ""
    lowered = real.lower()
    if any(pat.lower() in lowered for pat in DENIED_PATTERNS):
        logger.warning("LocalDiscovery denied path by denylist: %s", real)
        return ""
    return real

WORK_DIR = _safe_work_dir(os.getenv("HERMES_DISCOVERY_WORK_DIR", ""))
LOG_PATH = os.getenv("HERMES_DISCOVERY_LOG_PATH", "/opt/data/logs/gateway.log")
RECENT_FILE_EXTENSIONS = (".py", ".md", ".yaml", ".yml")

# P0 guardrails: LocalDiscovery must remain explicitly allowlisted and deny sensitive files.
DENIED_FILE_PATTERNS = (
    ".env", "auth.json", "storage_state.json", "cookie", "cookies",
    "token", "secret", "credential", "credentials", "api_key", "apikey",
    ".tar.gz", ".zip", "/private/", "/uploads/",
)
MAX_LOCAL_DISCOVERY_FILES = int(os.getenv("HERMES_DISCOVERY_MAX_FILES", "100"))
MAX_LOCAL_DISCOVERY_FILE_SIZE = int(os.getenv("HERMES_DISCOVERY_MAX_FILE_SIZE", "262144"))


MAX_TODO_RESULTS = int(os.getenv("HERMES_DISCOVERY_MAX_TODO_RESULTS", "5"))
MAX_COMMITS_PER_REPO = 5
MAX_ERROR_PATTERNS = 5
MAX_RECENT_FILES = int(os.getenv("HERMES_DISCOVERY_MAX_RECENT_FILES", "5"))

SOURCES_CONFIG_PATH = os.getenv(
    "HERMES_SOURCES_CONFIG",
    str(Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared")) / "sources.yaml"),
)
BUDGET_MAX_PER_RUN = int(os.getenv("HERMES_DISCOVERY_BUDGET_MAX_PER_RUN", "15"))
BUDGET_MAX_PER_SOURCE = int(os.getenv("HERMES_DISCOVERY_BUDGET_MAX_PER_SOURCE", "5"))
SHARE_THRESHOLD_MIN_SCORE = float(os.getenv("HERMES_DISCOVERY_SHARE_THRESHOLD_MIN_SCORE", "0.6"))

# Default sources config (used if sources.yaml not found)
DEFAULT_SOURCES_CONFIG: dict[str, Any] = {
    "sources": {
        "arxiv": {"enabled": True, "query": "(satellite AND smoke detection) OR (remote sensing AND computer vision) OR (wildfire AND deep learning)", "max_results": 3},
        "github": {"enabled": True, "query": "stars:>50 pushed:>2026-04-01", "sort": "stars", "per_page": 3},
        "hackernews": {"enabled": True, "max_stories": 15, "target_count": 3},
        "rss": {"enabled": False, "feeds": []},
    },
    "dedup": {"enabled": True, "url_cache_size": 200},
    "budgets": {"max_per_run": 15, "max_per_source": 5},
    "share_threshold": {"min_score": 0.6},
}


# ── External Discovery ──────────────────────────────────────────────────────────


class ExternalDiscovery:
    """Collect interesting content from free external APIs — arXiv, GitHub, HN."""

    def __init__(self, sources_config: dict[str, Any] | None = None) -> None:
        self._session: aiohttp.ClientSession | None = None
        self.sources_config = sources_config or {}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        return self._session

    async def collect(self) -> list[dict[str, Any]]:
        """Run all external collectors concurrently and return a merged list."""
        results: list[dict[str, Any]] = []
        if aiohttp is None:
            logger.debug("aiohttp not available; skipping external discovery")
            return results

        tasks: dict[str, Any] = {
            "arxiv": self._collect_arxiv(),
            "github": self._collect_github_trending(),
            "hn": self._collect_hacker_news(),
        }
        # Add RSS if enabled in sources config
        sources = self.sources_config.get("sources", {})
        if sources.get("rss", {}).get("enabled", False):
            tasks["rss"] = self._collect_rss()
        # Add Playwright if enabled in sources config
        if sources.get("playwright", {}).get("enabled", False):
            tasks["playwright"] = self._collect_playwright()
        # Add V2EX API if enabled
        if sources.get("v2ex", {}).get("enabled", False):
            tasks["v2ex"] = self._collect_v2ex()
        # Add Bilibili API if enabled
        if sources.get("bilibili", {}).get("enabled", False):
            tasks["bilibili"] = self._collect_bilibili()
        # Add 少数派 RSS if enabled
        if sources.get("sspai", {}).get("enabled", False):
            tasks["sspai"] = self._collect_sspai()

        # Run all collectors concurrently with asyncio.gather
        task_items = list(tasks.items())
        coros = [task for _, task in task_items]
        names = [name for name, _ in task_items]
        gathered = await asyncio.gather(*coros, return_exceptions=True)
        for source_name, result in zip(names, gathered):
            if isinstance(result, Exception):
                logger.exception("ExternalDiscovery[%s] failed: %s", source_name, result)
            else:
                items = result or []
                results.extend(items)
                logger.debug("ExternalDiscovery[%s]: %d items", source_name, len(items))

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

        return results

    async def _collect_arxiv(self) -> list[dict[str, Any]]:
        """Fetch recent papers from arXiv API in relevant fields."""
        session = await self._get_session()
        query = (
            "search_query="
            "(all:satellite AND all:smoke+detection)"
            "+OR+(all:remote+sensing AND all:computer+vision)"
            "+OR+(all:wildfire AND all:deep+learning)"
            "&sortBy=submittedDate&sortOrder=descending&max_results=3"
        )
        url = f"https://export.arxiv.org/api/query?{query}"
        headers = {"User-Agent": "HermesAlive/1.0 (discovery)"}

        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("arXiv API returned status %d", resp.status)
                return []
            text = await resp.text()

        return self._parse_arxiv_atom(text)

    def _parse_arxiv_atom(self, text: str) -> list[dict[str, Any]]:
        """Parse arXiv Atom XML into structured results."""
        import xml.etree.ElementTree as ET

        results: list[dict[str, Any]] = []
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            logger.exception("Failed to parse arXiv response")
            return []

        for entry in root.findall("atom:entry", ns)[:3]:
            title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ").replace("  ", " ")
            summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ").replace("  ", " ")

            # Truncate summary to a reasonable length
            if len(summary) > 300:
                summary = summary[:297] + "..."

            # Get the arXiv URL
            link_el = entry.find("atom:link", ns)
            url = ""
            if link_el is not None:
                url = link_el.get("href", "")

            results.append({
                "source": "arxiv",
                "title": title,
                "summary": summary,
                "url": url,
                "interesting_reason": "最近的相关研究论文",
            })

        return results

    async def _collect_v2ex(self) -> list[dict[str, Any]]:
        """Fetch hot topics from V2EX public JSON API."""
        session = await self._get_session()
        url = "https://www.v2ex.com/api/topics/hot.json"
        headers = {"User-Agent": "HermesAlive/1.0 (discovery)"}
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning("V2EX API returned status %d", resp.status)
                    return []
                data = await resp.json()
        except Exception:
            logger.exception("Failed to fetch V2EX hot topics")
            return []

        results: list[dict[str, Any]] = []
        max_results = self.sources_config.get("sources", {}).get("v2ex", {}).get("max_results", 3)
        for topic in data[:max_results]:
            title = (topic.get("title") or "").strip()
            topic_url = topic.get("url") or f"https://www.v2ex.com/t/{topic.get('id', '')}"
            if title:
                results.append({
                    "source": "v2ex",
                    "title": title,
                    "summary": f"节点:{topic.get('node', {}).get('title', '')} 回复:{topic.get('replies', 0)}",
                    "url": topic_url,
                })
        return results

    async def _collect_bilibili(self) -> list[dict[str, Any]]:
        """Fetch popular videos from Bilibili public JSON API."""
        session = await self._get_session()
        max_results = self.sources_config.get("sources", {}).get("bilibili", {}).get("max_results", 3)
        url = f"https://api.bilibili.com/x/web-interface/popular?ps={max_results}&pn=1"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning("Bilibili API returned status %d", resp.status)
                    return []
                data = await resp.json()
        except Exception:
            logger.exception("Failed to fetch Bilibili popular videos")
            return []

        results: list[dict[str, Any]] = []
        items = data.get("data", {}).get("list", [])
        for video in items[:max_results]:
            title = (video.get("title") or "").strip()
            bvid = video.get("bvid", "")
            video_url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
            stat = video.get("stat", {})
            summary = f"播放:{stat.get('view', 0)} 弹幕:{stat.get('danmaku', 0)}"
            if title:
                results.append({
                    "source": "bilibili",
                    "title": title,
                    "summary": summary,
                    "url": video_url,
                    "image_url": (
                        video.get("pic")
                        or ""
                    ).strip(),
                })
        return results

    async def _collect_sspai(self) -> list[dict[str, Any]]:
        """Fetch latest articles from 少数派 RSS feed."""
        import xml.etree.ElementTree as ET
        session = await self._get_session()
        url = "https://sspai.com/feed"
        headers = {
            "User-Agent": "HermesAlive/1.0 (discovery)",
            "Accept": "application/rss+xml, application/xml",
        }
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning("少数派 RSS returned status %d", resp.status)
                    return []
                text = await resp.text()
        except Exception:
            logger.exception("Failed to fetch 少数派 RSS")
            return []

        results: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            logger.warning("Failed to parse 少数派 RSS")
            return []

        max_results = self.sources_config.get("sources", {}).get("sspai", {}).get("max_results", 3)
        for item in root.findall(".//item")[:max_results]:
            title = (item.findtext("title", "") or "").strip()
            link = (item.findtext("link", "") or "").strip()
            description = (item.findtext("description", "") or "").strip()
            # Strip HTML tags from description for summary
            import re
            summary = re.sub(r"<[^>]+>", "", description)[:200] if description else ""
            if title:
                results.append({
                    "source": "sspai",
                    "title": title,
                    "summary": summary,
                    "url": link,
                })
        return results

    async def _collect_github_trending(self) -> list[dict[str, Any]]:
        """Fetch trending/recent GitHub repos."""
        session = await self._get_session()
        # Use GitHub search with reasonable limits to avoid rate limiting
        url = (
            "https://api.github.com/search/repositories"
            "?q=stars:>50+pushed:>2026-04-01&sort=stars&order=desc&per_page=3"
        )
        headers = {
            "User-Agent": "HermesAlive/1.0 (discovery)",
            "Accept": "application/vnd.github.v3+json",
        }

        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("GitHub API returned status %d; trying trending page", resp.status)
                return await self._collect_github_trending_scrape()

            data = await resp.json()
            items = data.get("items", [])
            results = []
            for repo in items[:3]:
                results.append({
                    "source": "github",
                    "title": repo.get("full_name", ""),
                    "description": repo.get("description") or "",
                    "url": repo.get("html_url", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "",
                })
            return results

    async def _collect_github_trending_scrape(self) -> list[dict[str, Any]]:
        """Fallback: scrape the GitHub trending page."""
        session = await self._get_session()
        url = "https://github.com/trending"
        headers = {"User-Agent": "HermesAlive/1.0 (discovery)"}

        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning("GitHub trending page returned status %d", resp.status)
                    return []
                text = await resp.text()
        except Exception:
            logger.exception("Failed to fetch GitHub trending page")
            return []

        return self._parse_trending_html(text)

    def _parse_trending_html(self, html: str) -> list[dict[str, Any]]:
        """Simple HTML parser for GitHub trending — looks for repo article blocks."""
        results: list[dict[str, Any]] = []
        # Simple parsing: find "h2" with repo links
        import re

        # Match patterns like: <h2 class="h3 lh-condensed">\n  <a href="/owner/repo">
        pattern = re.compile(
            r'href="/([^/"]+/[^/"]+)"[^>]*>.*?</a>',
            re.DOTALL,
        )
        # Find repo title blocks
        blocks = re.findall(
            r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>',
            html,
            re.DOTALL,
        )
        for block in blocks[:3]:
            match = re.search(r'href="/([^/"]+/[^/"]+)"', block)
            if not match:
                continue
            full_name = match.group(1)
            desc_match = re.search(
                r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>\s*(.*?)\s*</p>',
                block,
                re.DOTALL,
            )
            description = ""
            if desc_match:
                description = desc_match.group(1).strip()

            lang_match = re.search(
                r'<span[^>]*itemprop="programmingLanguage"[^>]*>\s*(.*?)\s*</span>',
                block,
            )
            language = lang_match.group(1).strip() if lang_match else ""

            results.append({
                "source": "github",
                "title": full_name,
                "description": description,
                "url": f"https://github.com/{full_name}",
                "language": language,
            })

        return results

    async def _collect_hacker_news(self) -> list[dict[str, Any]]:
        """Fetch top 3 interesting stories from Hacker News."""
        session = await self._get_session()

        # Get top stories
        async with session.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json"
        ) as resp:
            if resp.status != 200:
                logger.warning("HN topstories returned status %d", resp.status)
                return []
            story_ids = await resp.json()

        # Fetch individual stories (top 10 to filter interesting ones)
        results: list[dict[str, Any]] = []
        interesting_keywords = [
            "ai", "machine learning", "deep learning", "llm", "gpt",
            "programming", "software", "python", "rust", "go",
            "computer vision", "remote sensing", "satellite",
            "startup", "open source", "research", "paper",
        ]

        for sid in story_ids[:15]:
            if len(results) >= 3:
                break
            try:
                async with session.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                ) as resp:
                    if resp.status != 200:
                        continue
                    item = await resp.json()
                    if not item or not isinstance(item, dict):
                        continue
                    title = (item.get("title") or "").strip()
                    if not title:
                        continue

                    url = item.get("url") or f"https://news.ycombinator.com/item?id={sid}"

                    # Check if title is interesting
                    title_lower = title.lower()
                    is_interesting = any(kw in title_lower for kw in interesting_keywords)

                    if is_interesting:
                        results.append({
                            "source": "hn",
                            "title": title,
                            "url": url,
                        })
            except Exception:
                logger.debug("Failed to fetch HN item %d", sid, exc_info=True)
                continue

        # If we didn't find enough interesting ones, just add top ones
        if len(results) < 3:
            for sid in story_ids[:10]:
                if len(results) >= 3:
                    break
                try:
                    async with session.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                    ) as resp:
                        if resp.status != 200:
                            continue
                        item = await resp.json()
                        if not item or not isinstance(item, dict):
                            continue
                        title = (item.get("title") or "").strip()
                        if not title:
                            continue

                        already = any(r["url"].endswith(str(sid)) for r in results)
                        if already:
                            continue

                        url = item.get("url") or f"https://news.ycombinator.com/item?id={sid}"
                        results.append({
                            "source": "hn",
                            "title": title,
                            "url": url,
                        })
                except Exception:
                    continue

        return results

    async def _collect_rss(self) -> list[dict[str, Any]]:
        """Fetch items from configured RSS feeds using XML parsing."""
        sources = self.sources_config.get("sources", {})
        rss_config = sources.get("rss", {})
        feeds: list[dict[str, str]] = rss_config.get("feeds", [])
        if not feeds:
            logger.debug("RSS discovery: no feeds configured")
            return []

        session = await self._get_session()
        results: list[dict[str, Any]] = []
        import xml.etree.ElementTree as ET

        for feed in feeds:
            feed_url = feed.get("url", "")
            feed_name = feed.get("name", feed_url)
            if not feed_url:
                continue
            try:
                async with session.get(feed_url, headers={"User-Agent": "HermesAlive/1.0 (discovery)"}) as resp:
                    if resp.status != 200:
                        logger.warning("RSS feed %s returned status %d", feed_name, resp.status)
                        continue
                    text = await resp.text()
            except Exception:
                logger.exception("Failed to fetch RSS feed %s", feed_name)
                continue

            try:
                root = ET.fromstring(text)
            except ET.ParseError:
                logger.warning("Failed to parse RSS feed %s", feed_name)
                continue

            # Try RSS 2.0 format first, then Atom
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            channel = root.find("channel")
            items: list[Any] = []
            if channel is not None:
                # RSS 2.0
                for item in channel.findall("item"):
                    title = item.findtext("title", "").strip()
                    desc = item.findtext("description", "").strip()
                    link = item.findtext("link", "").strip()
                    items.append({
                        "source": "rss",
                        "title": title,
                        "summary": desc,
                        "url": link,
                        "feed_name": feed_name,
                    })
            else:
                # Atom
                for entry in root.findall("atom:entry", ns):
                    title = entry.findtext("atom:title", "", ns).strip()
                    summary = entry.findtext("atom:summary", "", ns).strip()
                    link_el = entry.find("atom:link", ns)
                    url = link_el.get("href", "") if link_el is not None else ""
                    items.append({
                        "source": "rss",
                        "title": title,
                        "summary": summary,
                        "url": url,
                        "feed_name": feed_name,
                    })

            results.extend(items)
            logger.debug("ExternalDiscovery[RSS][%s]: %d items", feed_name, len(items))

        return results

    async def _collect_playwright(self) -> list[dict[str, Any]]:
        """Visit configured Playwright URLs and extract visible text content.

        READ-ONLY: no clicks, no form filling, no interactions beyond page load.
        Never bypasses CAPTCHA, never stores passwords, never performs write actions.

        Supports site-specific extractors for forum-type sites (GitHub, HN, Reddit)
        that extract title links from listing pages using evaluate JS.
        Falls back to generic visible-text extraction for unknown/social sites.
        Individual site failures are caught and logged — they don't block other sites.
        Rate limiting with delay_between_pages config between requests.
        """
        import asyncio

        play_config = self.sources_config.get("sources", {}).get("playwright", {})
        if not play_config.get("enabled", False):
            return []

        try:
            from playwright.async_api import async_playwright  # type: ignore[import-untyped]
        except ImportError:
            logger.debug("Playwright not available; skipping playwright discovery")
            return []

        sites: list[dict[str, str]] = play_config.get("sites", [])
        if not sites:
            return []

        max_pages = play_config.get("max_pages_per_run", 5)
        timeout_ms = play_config.get("timeout_seconds", 20) * 1000
        delay_between = play_config.get("delay_between_pages", 2.0)

        results: list[dict[str, Any]] = []
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            )
            try:
                for i, site in enumerate(sites[:max_pages]):
                    url = site.get("url", "")
                    name = site.get("name", url)
                    site_type = site.get("type", "")
                    if not url:
                        continue
                    try:
                        # Chinese social platforms need mobile UA + anti-detection
                        is_social_site = any(d in url for d in ["xiaohongshu.com", "okjike.com"])
                        if is_social_site:
                            context = await browser.new_context(
                                viewport={"width": 400, "height": 800},
                                user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
                                locale="zh-CN",
                            )
                            await context.add_init_script("""
                                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                            """)
                        else:
                            context = await browser.new_context()
                        page = await context.new_page()
                        await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                        # Wait a moment for dynamic content to load
                        await page.wait_for_timeout(2000)

                        title = await page.title()
                        items: list[dict[str, Any]] = []

                        # Site-specific extractors — extract title links from listing pages
                        if "github.com" in url and "discussions" in url:
                            items = await self._extract_github_discussions(page, name, url)
                        elif "old.reddit.com" in url:
                            items = await self._extract_reddit_links(page, name, url)
                        elif "news.ycombinator.com" in url:
                            items = await self._extract_hn_links(page, name, url)
                        elif "zhihu.com" in url:
                            items = await self._extract_zhihu_hot(page, name, url)
                        elif "papers.cool" in url:
                            items = await self._extract_papers_cool(page, name, url)
                        elif "jandan.net" in url:
                            items = await self._extract_jandan(page, name, url)
                        elif "xiaohongshu.com" in url:
                            items = await self._extract_xiaohongshu(page, name, url)
                        else:
                            # Generic fallback: extract visible text
                            text = await page.evaluate(
                                """
                                () => {
                                    const body = document.body;
                                    if (!body) return '';
                                    return body.innerText.substring(0, 2000);
                                }
                                """
                            )
                            if text.strip():
                                items.append({
                                    "source": "playwright",
                                    "title": title or name,
                                    "summary": text.strip()[:500],
                                    "url": url,
                                    "site_name": name,
                                })

                        results.extend(items)
                        logger.debug(
                            "Playwright[%s]: %d items from %s", name, len(items), url
                        )
                        await context.close()

                    except Exception:
                        logger.debug("Playwright failed for %s: %s", name, url, exc_info=True)
                        continue
                    # Rate limiting: delay between requests (skip after last page)
                    if i < len(sites[:max_pages]) - 1:
                        await asyncio.sleep(delay_between)
            finally:
                await browser.close()

        return results

    async def _extract_github_discussions(
        self, page, name: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract discussion titles and links from a GitHub Discussions page."""
        items: list[dict[str, Any]] = []
        extracted = await page.evaluate(
            """
            () => {
                const links = document.querySelectorAll('a[href*="/discussions/"] h3, a[href*="/discussions/"] strong');
                const results = [];
                for (const el of links) {
                    const linkEl = el.closest('a');
                    if (!linkEl || !el.textContent) continue;
                    results.push({
                        title: el.textContent.trim(),
                        url: linkEl.href,
                    });
                }
                return results;
            }
            """
        )
        if not extracted:
            # Fallback: extract via link text
            extracted = await page.evaluate(
                """
                () => {
                    const articles = document.querySelectorAll('[class*="discussion"]');
                    const results = [];
                    for (const article of articles) {
                        const link = article.querySelector('a');
                        if (link && link.textContent && link.href) {
                            results.push({
                                title: link.textContent.trim(),
                                url: link.href,
                            });
                        }
                    }
                    return results;
                }
                """
            )

        for item in extracted or []:
            title = (item.get("title", "") or "").strip()
            url = (item.get("url", "") or "").strip()
            if title and url:
                items.append({
                    "source": "playwright",
                    "title": title,
                    "summary": "",
                    "url": url,
                    "site_name": name,
                })
        # Limit to top 15
        return items[:15]

    async def _extract_reddit_links(
        self, page, name: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract post titles and links from old.reddit.com listing."""
        items: list[dict[str, Any]] = []
        extracted = await page.evaluate(
            """
            () => {
                const entries = document.querySelectorAll('div.thing');
                const results = [];
                for (const entry of entries) {
                    const titleEl = entry.querySelector('a.title');
                    if (!titleEl || !titleEl.textContent) continue;
                    const url = titleEl.href;
                    const title = titleEl.textContent.trim();
                    const scoreEl = entry.querySelector('div.score.unvoted');
                    const score = scoreEl ? scoreEl.textContent.trim() : '';
                    const commentsEl = entry.querySelector('a.comments');
                    const comments = commentsEl ? commentsEl.textContent.trim() : '';
                    results.push({ title, url, score, comments });
                }
                return results.slice(0, 15);
            }
            """
        )
        for item in extracted or []:
            title = (item.get("title", "") or "").strip()
            url = (item.get("url", "") or "").strip()
            if title and url:
                summary = ""
                score = item.get("score", "")
                comments = item.get("comments", "")
                if score or comments:
                    summary = f"[{score} | {comments}]"
                items.append({
                    "source": "playwright",
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "site_name": name,
                })
        return items[:15]

    async def _extract_hn_links(
        self, page, name: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract story titles and links from news.ycombinator.com."""
        items: list[dict[str, Any]] = []
        extracted = await page.evaluate(
            """
            () => {
                const rows = document.querySelectorAll('tr.athing');
                const results = [];
                for (const row of rows) {
                    const titleEl = row.querySelector('td.title a');
                    if (!titleEl || !titleEl.textContent) continue;
                    const url = titleEl.href;
                    const title = titleEl.textContent.trim();
                    // Get score from the following row
                    const nextRow = row.nextElementSibling;
                    const subtext = nextRow ? nextRow.querySelector('td.subtext') : null;
                    const scoreEl = subtext ? subtext.querySelector('span.score') : null;
                    const score = scoreEl ? scoreEl.textContent.trim() : '';
                    results.push({ title, url, score });
                }
                return results.slice(0, 20);
            }
            """
        )
        for item in extracted or []:
            title = (item.get("title", "") or "").strip()
            url = (item.get("url", "") or "").strip()
            if title and url:
                summary = item.get("score", "")
                items.append({
                    "source": "playwright",
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "site_name": name,
                })
        return items[:15]

    async def _extract_zhihu_hot(
        self, page, name: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract hot topics from zhihu.com/hot — social site, extract visible text."""
        text = await page.evaluate(
            """
            () => {
                const body = document.body;
                if (!body) return '';
                return body.innerText.substring(0, 2000);
            }
            """
        )
        title = await page.title()
        items = []
        if text.strip():
            items.append({
                "source": "playwright",
                "title": title or name,
                "summary": text.strip()[:500],
                "url": base_url,
                "site_name": name,
            })
        return items

    async def _extract_papers_cool(
        self, page, name: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract arXiv papers from papers.cool listing page."""
        items: list[dict[str, Any]] = []
        extracted = await page.evaluate(
            """
            () => {
                const results = [];
                // papers.cool lists papers as cards with links
                const links = document.querySelectorAll('a[href*="arxiv.org"]');
                const seen = new Set();
                for (const link of links) {
                    const href = link.href;
                    const text = link.textContent.trim();
                    if (!text || seen.has(href)) continue;
                    seen.add(href);
                    results.push({ title: text, url: href });
                }
                // If no arxiv links found, try generic article links
                if (results.length === 0) {
                    const allLinks = document.querySelectorAll('article a, .paper-card a, .card a');
                    for (const link of allLinks) {
                        const text = link.textContent.trim();
                        if (!text || text.length < 5 || seen.has(link.href)) continue;
                        seen.add(link.href);
                        results.push({ title: text, url: link.href });
                    }
                }
                return results.slice(0, 15);
            }
            """
        )
        for item in extracted or []:
            title = (item.get("title", "") or "").strip()
            url = (item.get("url", "") or "").strip()
            if title and url:
                items.append({
                    "source": "playwright",
                    "title": title,
                    "summary": "",
                    "url": url,
                    "site_name": name,
                })
        return items[:15]

    async def _extract_jandan(
        self, page, name: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract article links from 煎蛋 (jandan.net) listing page."""
        items: list[dict[str, Any]] = []
        extracted = await page.evaluate(
            """
            () => {
                const results = [];
                // 煎蛋 article structure: posts in .post or #content with title links
                const postLinks = document.querySelectorAll('.post h2 a, .post h3 a, #content .indexs h2 a, .title2 a, .text h2 a');
                for (const link of postLinks) {
                    const text = link.textContent.trim();
                    if (!text) continue;
                    results.push({ title: text, url: link.href });
                }
                // Fallback: any h2/h3 links in the page
                if (results.length === 0) {
                    const allLinks = document.querySelectorAll('h2 a, h3 a');
                    for (const link of allLinks) {
                        const text = link.textContent.trim();
                        if (!text || text.length < 5) continue;
                        results.push({ title: text, url: link.href });
                    }
                }
                return results.slice(0, 15);
            }
            """
        )
        for item in extracted or []:
            title = (item.get("title", "") or "").strip()
            url = (item.get("url", "") or "").strip()
            if title and url:
                items.append({
                    "source": "playwright",
                    "title": title,
                    "summary": "",
                    "url": url,
                    "site_name": name,
                })
        return items[:15]

    async def _extract_xiaohongshu(
        self, page, name: str, base_url: str
    ) -> list[dict[str, Any]]:
        """Extract note cards from 小红书 explore page (anonymous, no login needed)."""
        items: list[dict[str, Any]] = []
        extracted = await page.evaluate(
            """
            () => {
                const results = [];
                const seen = new Set();

                // Extract from note links with image alt text
                const noteLinks = document.querySelectorAll('a[href*="/explore/"], a[href*="/discovery/item/"]');
                for (const link of noteLinks) {
                    const href = link.href;
                    if (!href || seen.has(href)) continue;
                    seen.add(href);

                    // Try to get meaningful title from nearby elements
                    let title = '';
                    let author = '';

                    // Get image alt as title (小红书 uses descriptive alt text)
                    const img = link.querySelector('img');
                    if (img && img.alt && img.alt.length > 2) {
                        title = img.alt.trim();
                    }

                    // Try title/desc elements
                    if (!title) {
                        const card = link.closest('section, [class*="note"], [class*="card"]');
                        if (card) {
                            const titleEl = card.querySelector('[class*="title"], [class*="desc"], h3');
                            title = titleEl ? titleEl.textContent.trim() : '';
                        }
                    }

                    // Get author from nearby
                    const card = link.closest('section, [class*="note"], [class*="card"]');
                    if (card) {
                        const authorEl = card.querySelector('[class*="author"], [class*="name"], .username');
                        author = authorEl ? authorEl.textContent.trim() : '';
                    }

                    if (title && title.length > 2) {
                        results.push({ title: title, url: href, author: author });
                    }
                }

                // Fallback: parse visible text for note-like content
                if (results.length < 3) {
                    const text = document.body.innerText;
                    const lines = text.split('\\n').filter(l => {
                        const t = l.trim();
                        return t.length > 5 && t.length < 100 &&
                               !t.includes('小红书') && !t.includes('App') &&
                               !t.includes('打开看看') && !t.includes('热门笔记') &&
                               !t.includes('生活指南');
                    });
                    for (const line of lines.slice(3, 18)) {
                        results.push({ title: line.trim(), url: '', author: '' });
                    }
                }

                return results.slice(0, 15);
            }
            """
        )
        for item in extracted or []:
            title = (item.get("title", "") or "").strip()
            url = (item.get("url", "") or "").strip()
            author = (item.get("author", "") or "").strip()
            if title:
                summary = f"作者:{author}" if author else ""
                items.append({
                    "source": "playwright",
                    "title": title,
                    "summary": summary,
                    "url": url or base_url,
                    "site_name": name,
                })
        return items[:15]


# ── Local Discovery ─────────────────────────────────────────────────────────────


class LocalDiscovery:
    """Scan local filesystem for interesting finds — TODOs, commits, errors, recent files."""

    def __init__(self) -> None:
        self.work_dir = WORK_DIR
        self.log_path = LOG_PATH

    async def collect(self) -> list[dict[str, Any]]:
        """Run all local collectors concurrently."""
        results: list[dict[str, Any]] = []

        # TODO/FIXME scan + git log + error log + recent files
        tasks = {
            "todo": self._scan_todos(),
            "git": self._scan_git_log(),
            "errors": self._scan_error_log(),
            "recent": self._scan_recent_files(),
        }

        task_items = list(tasks.items())
        coros = [task for _, task in task_items]
        names = [name for name, _ in task_items]
        gathered = await asyncio.gather(*coros, return_exceptions=True)
        for name, result in zip(names, gathered):
            if isinstance(result, Exception):
                logger.exception("LocalDiscovery[%s] failed: %s", name, result)
            else:
                items = result or []
                results.extend(items)
                logger.debug("LocalDiscovery[%s]: %d items", name, len(items))

        return results

    async def _scan_todos(self) -> list[dict[str, Any]]:
        """Recursively scan WORK_DIR for TODO/FIXME/HACK comments."""
        if not self.work_dir or not os.path.isdir(self.work_dir):
            return []
        loop = asyncio.get_running_loop()

        def _scan() -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            scanned = 0
            import re

            todo_pattern = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b\s*[:]?\s*(.*)", re.IGNORECASE)

            for root, _dirs, files in os.walk(self.work_dir):
                if scanned >= MAX_TODO_RESULTS * 2:
                    break
                for fname in files:
                    if not fname.endswith(RECENT_FILE_EXTENSIONS):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            for line_no, line in enumerate(f, 1):
                                match = todo_pattern.search(line)
                                if match:
                                    results.append({
                                        "type": "todo",
                                        "file": fpath,
                                        "line": str(line_no),
                                        "content": match.group(0).strip(),
                                    })
                                    scanned += 1
                                    if scanned >= MAX_TODO_RESULTS:
                                        break
                    except (OSError, UnicodeDecodeError):
                        continue
                if scanned >= MAX_TODO_RESULTS:
                    break
            return results

        return await loop.run_in_executor(None, _scan)

    async def _scan_git_log(self) -> list[dict[str, Any]]:
        """Check git log for recent interesting commits (last 24h) in each repo
        under WORK_DIR and in /opt/data."""
        repos = self._find_git_repos()
        results: list[dict[str, Any]] = []

        for repo_path in repos:
            try:
                commits = await self._git_log_since(repo_path, "24 hours ago")
                for commit in commits[:MAX_COMMITS_PER_REPO]:
                    results.append({
                        "type": "git",
                        "message": commit,
                        "repo": repo_path,
                    })
            except Exception:
                logger.debug("Failed to check git log for %s", repo_path, exc_info=True)

        return results

    def _find_git_repos(self) -> list[str]:
        """Find git repos in WORK_DIR subdirectories and /opt/data."""
        repos: list[str] = []

        # Check /opt/data
        opt_data = "/opt/data"
        if os.path.isdir(os.path.join(opt_data, ".git")):
            repos.append(opt_data)

        # Check work dir
        if not os.path.isdir(self.work_dir):
            return repos

        try:
            for entry in os.listdir(self.work_dir):
                git_path = os.path.join(self.work_dir, entry, ".git")
                if os.path.isdir(git_path):
                    repos.append(os.path.join(self.work_dir, entry))
        except OSError:
            pass

        return repos

    async def _git_log_since(self, repo_path: str, since: str) -> list[str]:
        """Run git log in a repo asynchronously."""
        cmd = ["git", "log", f"--since={since}", "--oneline", "--max-count=10"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode != 0:
                logger.debug("git log in %s failed: %s", repo_path, stderr.decode(errors="replace").strip())
                return []
            text = stdout.decode(errors="replace").strip()
            return [line.strip() for line in text.splitlines() if line.strip()]
        except asyncio.TimeoutError:
            logger.debug("git log in %s timed out", repo_path)
            return []
        except FileNotFoundError:
            logger.debug("git not found")
            return []

    async def _scan_error_log(self) -> list[dict[str, Any]]:
        """Look for ERROR/WARNING patterns in log file (last hour)."""
        loop = asyncio.get_running_loop()

        def _scan() -> list[dict[str, Any]]:
            if not os.path.isfile(self.log_path):
                return []

            import re
            from collections import Counter

            # In a real scenario we'd use timestamps; here we look at recent lines
            # by reading the tail of the file
            error_patterns: list[str] = []
            try:
                with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                    lines = all_lines[-200:]
            except Exception:
                return []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                # Look for ERROR and WARNING patterns
                if re.search(r"\b(ERROR|WARNING|CRITICAL)\b", stripped, re.IGNORECASE):
                    error_patterns.append(stripped)

            if not error_patterns:
                return []

            # Count patterns by their general category
            pattern_counts: Counter[str] = Counter()
            for ep in error_patterns:
                # Extract the meaningful part after the log level
                match = re.search(r"(ERROR|WARNING|CRITICAL)\s*[:-]\s*(.*)", ep, re.IGNORECASE)
                if match:
                    key = f"[{match.group(1).upper()}] {match.group(2).strip()[:80]}"
                else:
                    key = ep[:80]
                pattern_counts[key] += 1

            results = []
            for pattern, count in pattern_counts.most_common(MAX_ERROR_PATTERNS):
                results.append({
                    "type": "error",
                    "pattern": pattern,
                    "count": count,
                })
            return results

        return await loop.run_in_executor(None, _scan)

    async def _scan_recent_files(self) -> list[dict[str, Any]]:
        """Find recently modified files that might be interesting."""
        loop = asyncio.get_running_loop()

        def _scan() -> list[dict[str, Any]]:
            results: list[dict[str, Any]] = []
            import time as time_module

            now = time_module.time()
            seven_days = 7 * 24 * 3600

            candidates: list[tuple[str, float]] = []

            # Scan the work dir
            if os.path.isdir(self.work_dir):
                for root, _dirs, files in os.walk(self.work_dir):
                    for fname in files:
                        if not fname.endswith(RECENT_FILE_EXTENSIONS):
                            continue
                        fpath = os.path.join(root, fname)
                        try:
                            mtime = os.path.getmtime(fpath)
                            age = now - mtime
                            if age <= seven_days:
                                candidates.append((fpath, mtime))
                        except OSError:
                            continue

            # Sort by modification time (newest first)
            candidates.sort(key=lambda x: x[1], reverse=True)

            for fpath, mtime in candidates[:MAX_RECENT_FILES]:
                results.append({
                    "type": "recent_file",
                    "file": fpath,
                    "modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                })

            return results

        return await loop.run_in_executor(None, _scan)


# ── Scoring ─────────────────────────────────────────────────────────────────────


def _score_item(item: dict[str, Any]) -> float:
    """Score 0.0-1.0 based on basic heuristics."""
    score = 0.5  # neutral baseline
    title = (item.get("title", "") + " " + item.get("description", "")).lower()

    # Boost for relevant keywords
    keywords = [
        "ai", "llm", "agent", "smoke", "satellite", "fire", "detection",
        "python", "rust", "open source", "research", "paper", "architecture",
    ]
    for kw in keywords:
        if kw in title:
            score += 0.05

    # Boost for source authority
    if item.get("source") == "arxiv":
        score += 0.1
    elif item.get("source") in ("hn", "hackernews"):
        score += 0.05

    return min(score, 1.0)


# ── Discovery Engine ────────────────────────────────────────────────────────────


class DiscoveryEngine:
    """Orchestrates external and local discovery with caching and rate limiting.

    Usage:
        engine = DiscoveryEngine()
        if engine.should_run():
            results = await engine.collect()
        cached = engine.get_recent()
    """

    def __init__(self) -> None:
        # Load sources config
        self._sources_config = self._load_sources_config()
        self._external = ExternalDiscovery(sources_config=self._sources_config)
        self._local = LocalDiscovery()
        self._cached: dict[str, Any] | None = None
        self._last_fetch: float = 0.0
        self._in_progress: bool = False
        # URL-based dedup cache (in-memory, resets on gateway restart)
        self._url_cache: set[str] = set()
        self._interest_engine: Any | None = None

    def _interest(self) -> Any | None:
        # INTEREST_LEARNING_DISCOVERY_V1
        if self._interest_engine is None:
            try:
                from interest_learning import InterestLearningEngine
                self._interest_engine = InterestLearningEngine()
            except Exception:
                logger.exception("Failed to initialize interest learning engine")
                self._interest_engine = False
        return None if self._interest_engine is False else self._interest_engine

    def _load_sources_config(self) -> dict[str, Any]:
        """Load sources.yaml config with fallback to defaults."""
        path = SOURCES_CONFIG_PATH
        try:
            import yaml
            if os.path.isfile(path):
                with open(path, "r") as f:
                    cfg: dict[str, Any] = yaml.safe_load(f) or {}
                return cfg
        except Exception:
            logger.exception("Failed to load sources config from %s", path)
        return dict(DEFAULT_SOURCES_CONFIG)

    @property
    def interval_seconds(self) -> float:
        raw = os.getenv(DISCOVERY_INTERVAL_ENV)
        if raw is None or not raw.strip():
            return float(DEFAULT_DISCOVERY_INTERVAL)
        try:
            interval = float(raw)
        except ValueError:
            logger.warning("Invalid %s=%r; using default %.0f", DISCOVERY_INTERVAL_ENV, raw, DEFAULT_DISCOVERY_INTERVAL)
            return float(DEFAULT_DISCOVERY_INTERVAL)
        if interval <= 0:
            logger.warning("Invalid %s=%r; using default %.0f", DISCOVERY_INTERVAL_ENV, raw, DEFAULT_DISCOVERY_INTERVAL)
            return float(DEFAULT_DISCOVERY_INTERVAL)
        return interval

    def should_run(self) -> bool:
        """Check if enough time has passed since the last discovery run."""
        if self._in_progress:
            return False
        elapsed = time.monotonic() - self._last_fetch
        return elapsed >= self.interval_seconds

    async def collect(self) -> dict[str, Any]:
        """Run both external and local discovery, cache results, return them.

        Applies the following pipeline to external items:
          1. Deduplication (URL-based)
          2. Scoring (0.0-1.0 based on heuristics)
          3. Budget enforcement (max_per_run, max_per_source)
          4. Share threshold filtering

        Returns the full results dict with 'external', 'local', and 'fetched_at'.
        """
        self._in_progress = True
        try:
            external, local = await asyncio.gather(
                self._external.collect(),
                self._local.collect(),
                return_exceptions=True,
            )

            if isinstance(external, Exception):
                logger.error("External discovery failed: %s", external)
                external = []
            if isinstance(local, Exception):
                logger.error("Local discovery failed: %s", local)
                local = []

            # Apply pipeline to external items
            external = self._apply_pipeline(external)

            results: dict[str, Any] = {
                "external": external,
                "local": local,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

            self._cached = results
            self._last_fetch = time.monotonic()
            logger.info(
                "Discovery complete: %d external + %d local items",
                len(external),
                len(local),
            )
            return results
        finally:
            self._in_progress = False

    def _apply_pipeline(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply persistent dedup and interest-aware ranking."""
        interest = self._interest()
        if interest is not None:
            try:
                interest.sync_feedback_from_context()
            except Exception:
                logger.exception("Interest feedback sync failed")

        items = self._dedup(items)
        ranked: list[dict[str, Any]] = []
        for item in items:
            base_score = _score_item(item)
            if interest is not None:
                try:
                    item = interest.rank_item(item, base_score)
                    interest.record_ranked_item(item)
                except Exception:
                    logger.exception("Interest ranking failed")
                    item["score"] = base_score
            else:
                item["score"] = base_score
            ranked.append(item)

        ranked.sort(key=lambda value: float(value.get("score", 0.0)), reverse=True)
        ranked = self._filter_by_threshold(ranked)
        ranked = self._enforce_budget(ranked)
        return ranked

    def _dedup(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter out items with URLs already seen."""
        new_items: list[dict[str, Any]] = []
        for item in items:
            url = item.get("url", "")
            if url and url in self._url_cache:
                continue
            interest = self._interest()
            if interest is not None:
                try:
                    if interest.was_seen(item):
                        continue
                except Exception:
                    logger.exception("Persistent content dedup failed")
            if url:
                self._url_cache.add(url)
            new_items.append(item)
        return new_items

    def _enforce_budget(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enforce max_per_source and max_per_run budgets."""
        budgets = self._sources_config.get("budgets", {})
        max_per_run = budgets.get("max_per_run", BUDGET_MAX_PER_RUN)
        max_per_source = budgets.get("max_per_source", BUDGET_MAX_PER_SOURCE)

        # Enforce per-source cap
        source_counts: dict[str, int] = {}
        capped: list[dict[str, Any]] = []
        for item in items:
            source = item.get("source", "unknown")
            if source_counts.get(source, 0) >= max_per_source:
                continue
            source_counts[source] = source_counts.get(source, 0) + 1
            capped.append(item)

        # Enforce total cap
        return capped[:max_per_run]

    def _filter_by_threshold(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove items below the share threshold score."""
        threshold = self._sources_config.get("share_threshold", {}).get("min_score", SHARE_THRESHOLD_MIN_SCORE)
        return [item for item in items if item.get("score", 0.0) >= threshold]

    def get_recent(self) -> dict[str, Any] | None:
        """Return cached findings from the last run, or None."""
        return self._cached

    def has_fresh(self) -> bool:
        """Check if we have cached results that are still within the interval."""
        if self._cached is None:
            return False
        elapsed = time.monotonic() - self._last_fetch
        return elapsed < self.interval_seconds

    def clear_cache(self) -> None:
        self._cached = None
        self._last_fetch = 0.0
