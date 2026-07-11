# Platform Discovery Patterns

Systematic approach to researching and integrating new content platforms into Hermes Alive's discovery engine.

## Research Workflow (per platform)

1. **Official API first** — search for public API docs, try curl. Prefer JSON over HTML.
2. **RSS/Atom feed** — check `<link rel="alternate" type="application/rss+xml">` in page HTML.
3. **robots.txt** — `curl https://domain/robots.txt`, check disallowed paths.
4. **Simple HTTP** — `curl -sL` with browser UA to test access.
5. **Playwright fallback** — only if (3) allows and (4) is blocked by JS rendering.

## Platform Reference (2026-07-05)

### ✅ Working (implemented)

| Platform | Method | Extractor | Notes |
|----------|--------|-----------|-------|
| arXiv | aiohttp + Atom XML | `_collect_arxiv()` | Public API, no auth |
| GitHub Trending | aiohttp + JSON | `_collect_github_trending()` | API + HTML fallback |
| Hacker News | aiohttp + JSON | `_collect_hacker_news()` | Firebase API, keyword filter |
| V2EX | aiohttp + JSON | `_collect_v2ex()` | `/api/topics/hot.json`, public |
| Bilibili | aiohttp + JSON | `_collect_bilibili()` | Needs full Chrome UA to bypass code=-352 |
| 少数派 | aiohttp + RSS XML | `_collect_sspai()` | `/feed` RSS 2.0, codex misjudged as blocked |
| papers.cool | Playwright | `_extract_papers_cool()` | Anonymous HTML, arXiv listing |
| 煎蛋 | Playwright | `_extract_jandan()` | Anonymous HTML, article list |
| 小红书 | Playwright + anti-detection | `_extract_xiaohongshu()` | Needs mobile Chrome UA + webdriver conceal |
| 知乎热榜 | Playwright | `_extract_zhihu_hot()` | Generic text extraction |

### ❌ Blocked (not implemented)

| Platform | Reason |
|----------|--------|
| 即刻 | API: ruguoapp.com, needs QR login via app |
| 抖音 | Minimal content without auth |
| 微信公众号 | robots.txt: `Disallow: /` |
| Reddit ML | Cloudflare anti-bot |
| Hermes Forum | GitHub OAuth required |

## Anti-Detection for Chinese Social Platforms

小红书 (and similar Chinese platforms) detect headless Chrome. Required setup in `_collect_playwright()`:

```python
# Chrome launch args
browser = await pw.chromium.launch(headless=True, args=[
    '--disable-blink-features=AutomationControlled',
    '--no-sandbox',
])

# Mobile context for social sites
is_social = any(d in url for d in ["xiaohongshu.com", "okjike.com"])
if is_social:
    context = await browser.new_context(
        viewport={"width": 400, "height": 800},
        user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 9) ... Chrome/131.0.0.0 Mobile Safari/537.36",
        locale="zh-CN",
    )
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
    """)
else:
    context = await browser.new_context()  # Desktop for HN etc.
```

**Important**: Use `context.close()` not `page.close()` since each site gets its own browser context.

## Bilibili API Note

Bilibili public API returns code=-352 (risk control) with `User-Agent: HermesAlive/1.0`. Must use a full browser UA string:

```python
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ... Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
```

Tested working: `code=0` with full Chrome UA, `code=-352` with custom UA.

## Codex Sandbox Limitation

When delegating to Codex CLI for discovery.py modifications: `-s workspace-write` sandbox may fail with:
```
bwrap: Can't find source path /opt/data/.git: Permission denied
```

This blocks all file I/O. Workaround: Codex does the research/investigation, but file writes are handled by the agent directly (as done in this session).