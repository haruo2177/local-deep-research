# Phase 3.3 ツール実装計画（TDD）

**作成日**: 2026-01-17
**対象**: `src/tools/search.py`, `src/tools/scrape.py`
**開発方針**: TDD（テスト駆動開発）

---

## 概要

SearXNG APIクライアント（search.py）とCrawl4AIラッパー（scrape.py）のTDD実装を行う。

## 実装順序

1. **search.py** - SearXNG APIクライアント（外部依存が少なくシンプル）
2. **scrape.py** - Crawl4AIラッパー（ブラウザ依存あり）

---

## 1. search.py（SearXNG APIクライアント）

### 1.1 テストファイル作成: `tests/tools/test_search.py`

**テストケース:**

| # | テスト | 種別 | 優先度 |
|---|--------|------|--------|
| 1 | 正常検索で結果が返る | 正常系 | P0 |
| 2 | 検索結果0件で空リスト | 正常系 | P0 |
| 3 | SearchResultのフィールドが正しくマッピング | 正常系 | P0 |
| 4 | 空クエリでValueError | 異常系 | P0 |
| 5 | HTTPエラー（4xx/5xx）でSearchError | 異常系 | P0 |
| 6 | タイムアウトでSearchError | 異常系 | P1 |
| 7 | JSON解析エラーでSearchError | 異常系 | P1 |
| 8 | num_resultsで結果数制限 | 正常系 | P1 |
| 9 | settingsからURLを取得する | 正常系 | P0 |

**モック戦略:** `aioresponses` を使用してHTTPリクエストをモック

### 1.2 実装: `src/tools/search.py`

**関数シグネチャ:**
```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    engine: Optional[str] = None

class SearchError(Exception):
    """Exception raised when search fails."""
    pass

async def search(
    query: str,
    *,
    num_results: int = 10,
    timeout: float = 10.0,
) -> list[SearchResult]:
    """Search using SearXNG and return results."""
    ...
```

**SearXNG API仕様:**
- エンドポイント: `GET /search?q={query}&format=json`
- レスポンス形式:
```json
{
  "results": [
    {"title": "...", "url": "...", "content": "...", "engine": "google"}
  ]
}
```

---

## 2. scrape.py（Crawl4AIラッパー）

### 2.1 テストファイル作成: `tests/tools/test_scrape.py`

**テストケース:**

| # | テスト | 種別 | 優先度 |
|---|--------|------|--------|
| 1 | 正常スクレイプでMarkdownが返る | 正常系 | P0 |
| 2 | ScrapeResultのフィールドが正しく設定 | 正常系 | P0 |
| 3 | 空URLでValueError | 異常系 | P0 |
| 4 | 無効なURL形式でValueError | 異常系 | P0 |
| 5 | スクレイプ失敗でsuccess=False | 正常系 | P0 |
| 6 | タイムアウトでsuccess=False | 異常系 | P1 |
| 7 | max_content_lengthで切り詰め | 正常系 | P1 |
| 8 | scrape_multipleで複数URL処理 | 正常系 | P1 |
| 9 | 一部失敗でも残りは継続処理 | 正常系 | P1 |

**モック戦略:** `unittest.mock.patch` で `AsyncWebCrawler` をモック

### 2.2 実装: `src/tools/scrape.py`

**関数シグネチャ:**
```python
@dataclass
class ScrapeResult:
    url: str
    markdown: str
    success: bool
    error_message: Optional[str] = None
    title: Optional[str] = None

class ScrapeError(Exception):
    """Exception raised when scraping fails."""
    pass

async def scrape(
    url: str,
    *,
    timeout: float = 30.0,
    max_content_length: int = 50000,
) -> ScrapeResult:
    """Scrape a URL and return markdown content."""
    ...

async def scrape_multiple(
    urls: list[str],
    *,
    timeout: float = 30.0,
    max_content_length: int = 50000,
) -> list[ScrapeResult]:
    """Scrape multiple URLs sequentially."""
    ...
```

---

## 変更対象ファイル

| ファイル | 操作 |
|---------|------|
| `tests/tools/test_search.py` | 新規作成 |
| `src/tools/search.py` | 実装 |
| `tests/tools/test_scrape.py` | 新規作成 |
| `src/tools/scrape.py` | 実装 |

**参照ファイル:**
- `tests/conftest.py` - 既存フィクスチャ（`mock_searxng_url`, `sample_search_results`）
- `src/config.py` - 設定取得パターン

---

## TDDサイクル

各ツールについて:

1. **Red**: テストファイルを作成し、`uv run pytest tests/tools/test_*.py` で失敗を確認
2. **Green**: 最小限の実装でテストを通す
3. **Refactor**: コードを整理、型ヒントを追加

---

## 検証方法

```bash
# 単体テスト実行
uv run pytest tests/tools/ -v

# カバレッジ付き
uv run pytest tests/tools/ --cov=src/tools --cov-report=term-missing

# 型チェック
uv run mypy src/tools/

# リンター
uv run ruff check src/tools/
```

**統合テスト（手動確認）:**
```bash
# SearXNG動作確認
curl "http://localhost:8080/search?q=test&format=json"
```

---

## 次のステップ

Phase 3.3完了後:
- Phase 3.4: `prompts/templates.py` のテスト作成
- Phase 4: 各ノード（`nodes/*.py`）のTDD実装
