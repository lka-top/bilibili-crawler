# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
uv sync                           # install dependencies
uv run playwright install chromium # install browser driver
uv run python main.py             # interactive mode
```

```bash
python main.py -k "关键词1,关键词2"  # search mode
python main.py -b "BV1xx,BV2yy"    # detail mode (BV IDs)
```

## Tests

```bash
python -m pytest test_video_crawler.py -v   # main test suite (unittest)
python test_quick.py                         # quick smoke test
```

## Architecture

This is an async Bilibili video crawler using **Playwright** (browser automation with stealth.js) + **httpx** (signed API calls). The entry point is `main.py` → `cli()` → `asyncio.run(main())`.

**Data flow:** CLI args → `BilibiliCrawler.start()` (browser → login → WBI key init → fetch data) → `StorageManager.save()` → `ReportGenerator.generate()`

**Key modules:**
- `config/` — pydantic-settings `Settings` from `.env` (prefix `BILI_`), plus Bilibili API constants/URLs/selectors
- `core/browser.py` — `BrowserManager`: wraps Playwright Chromium with `stealth.js` anti-detection
- `login/auth.py` — `BilibiliLogin`: QR-code login (displays image, polls 120s) or cookie injection
- `client/bilibili_client.py` — `BilibiliClient`: httpx API client with WBI signing (keys from localStorage or API fallback)
- `crawler/spider.py` — `BilibiliCrawler`: orchestrates browser → login → client → data collection; random delays between requests via `_random_delay()`
- `models/bilibili.py` — `BilibiliVideo` (24-field Pydantic model) and `BilibiliSearchResponse`
- `store/backend.py` — `StorageManager` delegating to `JSONStorage` or `CSVStorage` (strategy pattern)
- `analysis/report.py` — `ReportGenerator`/`BilibiliAnalyzer`: produces markdown report + wordcloud PNG
- `tools/sign.py` — `BilibiliSign`: WBI signature algorithm (MD5-based), URL parsers
- `proxy/pool.py` — `ProxyPool`: proxy management (declared but not wired into the main pipeline)

**Global singleton:** `from config import settings` — imported everywhere, mutated via `settings.keywords = ...` etc. before `asyncio.run(main())`.

## Important patterns

- **Module-level `sys.path` hacks:** `client/`, `crawler/`, and `main.py` all do `sys.path.insert(0, str(Path(__file__).parent.parent))` so scripts work without package install.
- **Optional dependency guards:** Every external import uses `try/except ImportError` with `HAS_*` flags — if a library is missing, the feature degrades rather than crashing.
- **Login state is persisted** via Playwright's `user_data_dir` (`BILI_BROWSER_USER_DATA_DIR`), not manual cookie files.
- **`test_quick.py` imports `ContentCrawler`** which does not exist in `crawler/spider.py` — this file is a legacy prototype and should not be relied on.
