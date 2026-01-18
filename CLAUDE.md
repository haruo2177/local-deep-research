# CLAUDE.md - プロジェクト開発ガイドライン

## 開発方針: TDD（テスト駆動開発）

このプロジェクトはTDDを前提として開発を進める。

### TDDの基本サイクル

1. **Red**: 失敗するテストを先に書く
2. **Green**: テストが通る最小限の実装を書く
3. **Refactor**: コードをリファクタリングする

### TDDが適用できる領域

| コンポーネント | テスト可能性 | テスト方法 |
|---------------|-------------|-----------|
| 状態定義 (`state.py`) | 高 | 単体テスト: 状態の型チェック、初期値検証 |
| プロンプトテンプレート (`prompts/`) | 高 | 単体テスト: テンプレート展開の検証 |
| 検索ツール (`tools/search.py`) | 中 | 統合テスト: モックサーバーを使用 |
| スクレイピングツール (`tools/scrape.py`) | 中 | 統合テスト: ローカルHTMLファイルを使用 |
| 各ノード (`nodes/`) | 中 | 単体テスト: モックLLMレスポンスを使用 |
| グラフ構築 (`graph.py`) | 高 | 単体テスト: グラフ構造の検証 |

### TDDが困難な領域と確認方法

| コンポーネント | 困難な理由 | 確認方法 |
|---------------|-----------|---------|
| LLM出力の品質 | 非決定的な出力 | 手動確認 + 出力ログの保存 |
| Docker環境 | 外部依存 | 起動スクリプト + ヘルスチェック |
| Ollama連携 | 外部サービス | 接続テスト + サンプルクエリ実行 |
| SearXNG連携 | 外部サービス | 接続テスト + サンプル検索実行 |
| エンドツーエンド | 複合的な依存 | 手動シナリオテスト + 結果レビュー |

### 実装時のルール

1. **新機能を実装する前に、必ずテストファイルを先に作成する**
2. **テストが失敗することを確認してから実装に進む**
3. **外部依存がある場合は、モックを使用した単体テストを作成する**
4. **TDDが困難な部分は、確認手順を文書化してから実装する**

### テストの実行

```bash
# 全テストの実行
uv run pytest

# 特定のテストファイルを実行
uv run pytest tests/test_state.py

# カバレッジレポート付き
uv run pytest --cov=src --cov-report=html
```

### 確認手順のテンプレート（TDDが困難な場合）

```markdown
## 確認項目: [コンポーネント名]

### 前提条件
- [ ] Docker環境が起動している
- [ ] Ollamaにモデルがロードされている

### 確認手順
1. [具体的な操作手順]
2. [期待される結果]

### 成功基準
- [ ] [具体的な成功条件]

### 確認日時
- YYYY-MM-DD HH:mm: [結果]
```

---

## 実装ログ

実装作業の記録は `docs/logs/` ディレクトリに日付ベースで保存する。

### ファイル命名規則
```
docs/logs/YYYYMMDD-HHmmss-description.md
```

例: `docs/logs/20260117-143000-phase3-tools.md`

### ログの作成タイミング
- **セッション開始時**: 新しいログファイルを作成し、目標を記載
- **作業中**: 完了タスク、問題と解決策を随時追記
- **セッション終了時**: 次回への引き継ぎを記載

### 記録すべき内容
1. **完了したタスク**: チェックリスト形式で記録
2. **TDD記録**: 書いたテストとその結果
3. **問題と解決策**: 遭遇した問題と解決方法
4. **学んだこと**: 新しい知見や気づき
5. **次回への引き継ぎ**: 未完了タスクや確認事項

テンプレートは `docs/logs/TEMPLATE.md` を参照。

---

## プロジェクト構造

```
pyproject.toml           # プロジェクト設定・依存関係
.python-version          # Python バージョン (3.13)
docker-compose.yaml      # Docker構成（Ollama + SearXNG）
searxng/
└── settings.yml         # SearXNG設定

docs/
├── plans/               # 実装計画
│   └── YYYYMMDD-HHmmss-description.md
└── logs/                # 実装ログ
    ├── TEMPLATE.md
    └── YYYYMMDD-HHmmss-description.md

src/
├── __init__.py
├── main.py              # CLIエントリーポイント
├── config.py            # 設定管理
├── state.py             # ResearchState TypedDict
├── graph.py             # LangGraphワークフロー定義
├── llm.py               # LLMユーティリティ
├── nodes/
│   ├── planner.py       # 計画ノード
│   ├── researcher.py    # 調査ノード
│   ├── scraper.py       # スクレイピング・要約ノード
│   ├── reviewer.py      # 評価ノード
│   └── writer.py        # 執筆ノード
├── tools/
│   ├── search.py        # SearXNG連携
│   └── scrape.py        # Crawl4AI連携
└── prompts/
    └── templates.py     # プロンプトテンプレート

tests/
├── __init__.py
├── conftest.py          # pytest fixtures
├── test_state.py
├── test_config.py
├── test_graph.py
├── test_llm.py
├── test_main.py
├── test_prompts.py
├── nodes/
│   ├── test_planner.py
│   ├── test_researcher.py
│   ├── test_scraper.py
│   ├── test_reviewer.py
│   └── test_writer.py
├── tools/
│   ├── test_search.py
│   └── test_scrape.py
└── integration/
    ├── test_error_handling.py
    └── test_workflow.py
```

## コマンド

**注意**: 全てのコマンドはプロジェクトルートから実行する。`git -C` 等のパス指定は不要。

```bash
# 環境セットアップ
uv sync                           # 依存関係インストール

# Docker環境
docker compose up -d              # サービス起動
docker compose down               # サービス停止
docker compose ps                 # 状態確認

# Ollama操作
docker exec ollama ollama list              # モデル一覧
docker exec ollama ollama pull <model>      # モデル取得
docker exec ollama nvidia-smi               # GPU確認

# ヘルスチェック
curl http://localhost:11434/api/tags                      # Ollama API
curl http://localhost:8080/healthz                        # SearXNG
curl "http://localhost:8080/search?q=test&format=json"    # SearXNG JSON API

# 研究実行
uv run python -m src.main "リサーチトピック"              # Deep Research実行
uv run python -m src.main --output report.md "トピック"   # ファイル出力付き
uv run python -m src.main --demo search "クエリ"          # 検索デモ
uv run python -m src.main --demo plan "タスク"            # 計画デモ

# テスト実行
uv run pytest                     # 全テスト
uv run pytest --cov=src           # カバレッジ付き

# 型チェック
uv run mypy src/

# リンター・フォーマッター
uv run ruff check src/ tests/     # リンター
uv run ruff format src/ tests/    # フォーマッター
```

---

## ドキュメントのメンテナンス

### CLAUDE.md の更新ルール

`git push` 後に以下を確認し、乖離があれば修正する：

1. **プロジェクト構造**: 新規ファイル/ディレクトリが反映されているか
2. **コマンド**: 新しい操作コマンドが追加されているか
3. **TDD領域**: テスト方法の変更があれば更新

### 更新タイミング

- 新しいフェーズの実装完了時
- プロジェクト構造に変更があった時
- 開発フローに変更があった時
