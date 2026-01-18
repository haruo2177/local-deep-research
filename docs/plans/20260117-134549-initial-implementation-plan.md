# ローカルDeep Researchシステム 実装計画

**作成日**: 2026-01-17
**最終更新**: 2026-01-18
**ベースドキュメント**: [initial-plan.md](initial-plan.md)
**開発方針**: TDD（テスト駆動開発）

---

## 進捗サマリー

| フェーズ | 内容 | 状態 |
|---------|------|------|
| 1.1 | Docker環境セットアップ | ✅ 完了 |
| 1.2 | モデル準備 | ✅ 完了 |
| 2.1 | プロジェクト初期化 | ✅ 完了 |
| 2.2 | 依存ライブラリ | ✅ 完了 |
| 3.1 | config.py | ✅ 完了（8テスト） |
| 3.2 | state.py | ✅ 完了（12テスト） |
| 3.3 | ツール実装 | ✅ 完了（26テスト） |
| 3.4 | プロンプトテンプレート | ✅ 完了（13テスト） |
| 3.5 | デモモード | ✅ 完了（6テスト） |
| 4.x | LangGraphノード | ✅ 完了（51テスト） |
| 5.x | グラフ構築 | ✅ 完了（18テスト） |

**テスト**: 134テストパス / カバレッジ 95%

---

## 開発方針

本プロジェクトはTDD（テスト駆動開発）を前提として進める。

### TDDサイクル
1. **Red**: 失敗するテストを先に書く
2. **Green**: テストが通る最小限の実装を書く
3. **Refactor**: コードをリファクタリングする

### TDDが困難な領域の確認方法
外部依存（Docker、Ollama、SearXNG等）がある部分は、確認手順を文書化してから実装する。
詳細は [CLAUDE.md](../../CLAUDE.md) を参照。

---

## 概要

GTX 1660 SUPER（6GB VRAM）環境で動作する自律型Deep Researchエージェントを構築する。LangGraphを用いたグラフベースのワークフロー、Ollamaによるローカル推論、SearXNGによるプライバシー重視の検索、Crawl4AIによるスクレイピングを組み合わせる。

---

## フェーズ1: 基盤環境の構築

> **TDD適用**: 困難（外部依存）
> **確認方法**: ヘルスチェックスクリプトで動作確認

### 1.1 Docker環境のセットアップ ✅ 完了
- [x] NVIDIA Container Toolkitのインストール確認
- [x] `docker-compose.yaml`の作成
  - Ollamaサービス（GPU対応、Flash Attention有効化）
  - SearXNGサービス（メタ検索エンジン）
- [x] SearXNG設定ファイルの作成（`searxng/settings.yml`）
  - 使用する検索エンジンの選定（Google, Bing, DuckDuckGo, Wikipedia, arXiv, Semantic Scholar）
  - JSON API出力の有効化

### 1.2 モデルの準備 ✅ 完了
- [x] Plannerモデル: `deepseek-r1:7b`のプル（4.7GB）
- [x] Workerモデル: `qwen2.5:3b`のプル（1.9GB）
- [x] 各モデルのVRAM使用量検証

### 1.3 確認手順（TDD代替）
```bash
# Ollamaヘルスチェック
curl http://localhost:11434/api/tags

# SearXNGヘルスチェック
curl "http://localhost:8080/search?q=test&format=json"

# GPU認識確認
docker exec ollama nvidia-smi
```

**成果物**:
- `docker-compose.yaml`
- `searxng/settings.yml`
- 動作確認済みのOllama + SearXNG環境

---

## フェーズ2: Pythonプロジェクト構造の構築 ✅ 完了

> **TDD適用**: 可能
> **方針**: テストインフラを先に構築

### 2.1 プロジェクト初期化 ✅ 完了
- [x] `pyproject.toml`の作成（pytest, mypy, ruff含む）
- [x] `.python-version`の作成（Python 3.10）
- [x] 仮想環境のセットアップ（uv使用、128パッケージインストール）
- [x] `tests/conftest.py`の作成（共通fixture定義）
- [x] `pytest`が実行できることを確認（20テストパス）

### 2.2 依存ライブラリ ✅ インストール済み
```
# 本体
langgraph>=0.6.0
langchain-ollama>=0.2.0
langchain-core>=0.3.0
crawl4ai>=0.4.0
aiohttp>=3.9.0
pydantic>=2.0.0

# 開発用
pytest>=8.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.23.0
mypy>=1.8.0
ruff>=0.4.0
```

### 2.3 ディレクトリ構造
```
local-deep-research/
├── docker-compose.yaml
├── searxng/
│   └── settings.yml
├── src/
│   ├── __init__.py
│   ├── main.py              # エントリーポイント
│   ├── config.py            # 設定管理
│   ├── state.py             # LangGraph状態定義
│   ├── graph.py             # グラフ構築
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── planner.py       # 計画ノード
│   │   ├── researcher.py    # 調査ノード
│   │   ├── scraper.py       # スクレイピング・要約ノード
│   │   ├── reviewer.py      # 評価ノード
│   │   └── writer.py        # 執筆ノード
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── search.py        # SearXNG連携
│   │   └── scrape.py        # Crawl4AI連携
│   └── prompts/
│       └── templates.py     # プロンプトテンプレート
├── tests/
│   └── ...
└── README.md
```

**成果物**:
- プロジェクト骨格
- 依存関係定義ファイル

---

## フェーズ3: コアコンポーネントの実装

> **TDD適用**: 可能
> **方針**: 各モジュールでテストを先に書く

### 3.1 設定管理 (`config.py`) ✅ 完了

**テストファースト**: `tests/test_config.py`を先に作成（8テスト）
- [x] Ollamaエンドポイント設定（環境変数対応）
- [x] SearXNGエンドポイント設定（環境変数対応）
- [x] モデル名の定義（Planner: deepseek-r1:7b / Worker: qwen2.5:3b）
- [x] コンテキスト長制限の設定（max_context_length, max_iterations）

### 3.2 状態定義 (`state.py`) ✅ 完了

**テストファースト**: `tests/test_state.py`を先に作成（12テスト）
- [x] `ResearchState` TypedDictの実装
  - `task`: ユーザーの元の質問
  - `plan`: 検索計画（サブクエリリスト）
  - `steps_completed`: 実行ステップ数
  - `content`: 要約済み情報リスト（Annotated + operator.add）
  - `current_search_query`: 現在のクエリ
  - `references`: 引用元URLリスト（Annotated + operator.add）
  - `is_sufficient`: 情報充足フラグ

### 3.3 ツール実装 ✅ 完了

#### 3.3.1 検索ツール (`tools/search.py`) ✅ 完了

**テストファースト**: `tests/tools/test_search.py`を先に作成（13テスト）
- [x] SearXNG APIクライアントの実装（aiohttp使用）
- [x] 検索結果のパース（SearchResult dataclass）
- [x] エラーハンドリング（SearchError）

#### 3.3.2 スクレイピングツール (`tools/scrape.py`) ✅ 完了

**テストファースト**: `tests/tools/test_scrape.py`を先に作成（13テスト）
- [x] Crawl4AIの初期化と設定（AsyncWebCrawler）
- [x] Markdown変換機能の利用
- [x] メモリ管理（scrape_multiple: 順次処理）
- [x] タイムアウト・エラーハンドリング（ScrapeResult.success=False）

### 3.4 プロンプトテンプレート (`prompts/templates.py`) ✅ 完了

**テストファースト**: `tests/test_prompts.py`を先に作成（13テスト）
- [x] Planner用プロンプト（JSON出力強制）
- [x] Summarizer用プロンプト（max_length対応）
- [x] Reviewer用プロンプト（情報充足判定、JSON形式）
- [x] Writer用プロンプト（レポート生成）
- [x] 各テンプレートのフォーマット関数

### 3.5 デモモード (`main.py`) ✅ 完了

**テストファースト**: `tests/test_main.py`を先に作成（6テスト）
- [x] `--demo search` で検索ツールの動作確認
- [x] `--demo scrape` でスクレイピングツールの動作確認
- [x] `--demo plan` でPlannerノードの動作確認
- [x] `--demo summarize` でLLM要約の動作確認

**成果物**:
- ✅ 設定管理モジュール（実装済み）
- ✅ 状態定義（実装済み）
- ✅ 検索ツール（実装済み、13テスト）
- ✅ スクレイピングツール（実装済み、13テスト）
- ✅ プロンプトテンプレート集（実装済み、13テスト）
- ✅ デモモード（実装済み、4テスト）

---

## フェーズ4: LangGraphノードの実装 ✅ 完了

> **TDD適用**: 完全適用（モックLLMレスポンス使用）
> **方針**: モックLLMレスポンスを使用してロジックをテスト
> **テスト**: 51テスト（llm: 7, planner: 11, researcher: 8, scraper: 8, reviewer: 9, writer: 8）

### 4.0 LLMユーティリティ (`llm.py`) ✅ 完了

**テストファースト**: `tests/test_llm.py`（7テスト）
- [x] langchain_ollama統合
- [x] タイムアウト・接続エラーハンドリング
- [x] LLMError例外クラス

### 4.1 Plannerノード (`nodes/planner.py`) ✅ 完了

**テストファースト**: `tests/nodes/test_planner.py`（11テスト）
- [x] DeepSeek R1モデルの呼び出し
- [x] ユーザー入力からサブクエリへの分解
- [x] JSON出力のパースとバリデーション
- [x] パース失敗時のリトライロジック（最大3回）
- [x] PlannerError例外クラス

### 4.2 Researcherノード (`nodes/researcher.py`) ✅ 完了

**テストファースト**: `tests/nodes/test_researcher.py`（8テスト）
- [x] 計画に基づく検索クエリの発行
- [x] SearXNGツールの呼び出し
- [x] URLリストの状態への保存
- [x] 重複URLのスキップ

### 4.3 Scraper & Summarizerノード (`nodes/scraper.py`) ✅ 完了

**テストファースト**: `tests/nodes/test_scraper.py`（8テスト）
- [x] URLからのコンテンツ取得（Crawl4AI）
- [x] Workerモデル（Qwen 2.5 3B）による即時要約
- [x] 要約結果の状態への追加
- [x] 参照URLの記録
- [x] 長いコンテンツのトランケート（10000文字）

### 4.4 Reviewerノード (`nodes/reviewer.py`) ✅ 完了

**テストファースト**: `tests/nodes/test_reviewer.py`（9テスト）
- [x] 収集情報の充足度判定
- [x] 不足時: Researcherへの戻り指示
- [x] 充足時: Writerへの進行指示
- [x] `should_continue_research` 条件付きエッジ関数

### 4.5 Writerノード (`nodes/writer.py`) ✅ 完了

**テストファースト**: `tests/nodes/test_writer.py`（8テスト）
- [x] 蓄積情報の統合
- [x] 最終レポートの生成（DeepSeek R1使用）
- [x] 引用元URLの明記
- [x] WriterError例外クラス

**成果物**:
- ✅ 全5ノードの実装
- ✅ LLMユーティリティ
- ✅ 各ノードの単体テスト（51テスト）

---

## フェーズ5: グラフの構築と統合 ✅ 完了

> **TDD適用**: 完全適用
> **方針**: グラフ構造のテスト + モックノードを使用した統合テスト
> **テスト**: 18テスト（graph: 14, main追加: 4）

### 5.1 グラフ定義 (`graph.py`) ✅ 完了

**テストファースト**: `tests/test_graph.py`（14テスト）
- [x] StateGraphの初期化
- [x] 各ノードの追加（planner, researcher, scraper, reviewer, writer）
- [x] エッジ（遷移）の定義
  - START → Planner
  - Planner → Researcher
  - Researcher → Scraper
  - Scraper → Reviewer
  - Reviewer → Researcher（ループ）または Writer
  - Writer → END
- [x] 条件付きエッジの実装（Reviewer判定による分岐）

### 5.2 グラフのコンパイルと実行 ✅ 完了
- [x] グラフのコンパイル
- [x] 入力・出力インターフェースの定義

### 5.3 エントリーポイント (`main.py`) ✅ 完了

**テストファースト**: `tests/test_main.py`（4テスト追加）
- [x] `run_research()` 関数の実装
- [x] CLIインターフェースの実装
- [x] 非同期実行のセットアップ
- [x] 結果の出力（Markdown形式）
- [x] `--output` フラグによるファイル出力

**成果物**:
- ✅ 完成したLangGraphワークフロー
- ✅ 実行可能なCLIアプリケーション
- ✅ グラフ構造のテスト（14テスト）
- ✅ フル実行モードのテスト（4テスト）

---

## フェーズ6: 最適化と品質保証

> **TDD適用**: 部分的に可能
> **方針**: エラーハンドリングはTDD、パフォーマンスは手動計測

### 6.1 VRAM最適化

**確認方法**: 手動計測 + ログ記録
- [ ] 実際のメモリ使用量の計測（nvidia-smi）
- [ ] コンテキスト長の調整
- [ ] モデル切り替えのバッチ化検討

### 6.2 エラーハンドリング強化

**テストファースト**: 各モジュールのエラーケーステストを追加
- [ ] ネットワークエラーのリトライ
- [ ] モデル出力のバリデーション
- [ ] タイムアウト処理

### 6.3 統合テスト

**テストファースト**: `tests/integration/`を作成
- [ ] エンドツーエンドテスト（モックサービス使用）
- [ ] パフォーマンステスト（処理時間、メモリ使用量）

### 6.4 テストカバレッジ目標
- 単体テスト: 80%以上
- 統合テスト: 主要フロー100%

**成果物**:
- 完成したテストスイート
- パフォーマンスレポート

---

## フェーズ7: ドキュメントと仕上げ

### 7.1 ドキュメント
- [ ] README.md（セットアップ手順、使用方法）
- [ ] 設定オプションの説明

### 7.2 オプション機能
- [ ] 進捗表示（ストリーミング出力）
- [ ] レポートのファイル保存
- [ ] 簡易WebUI（Open WebUI連携など）

---

## 技術的考慮事項

### メモリ管理の原則
1. **即時要約**: 生データは即座に要約してコンテキストを節約
2. **モデルのバッチ処理**: 同じモデルを使うタスクをまとめて実行
3. **VRAMファースト**: システムRAMへのオフロードを避ける

### Ollama環境変数（必須）
```bash
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KEEP_ALIVE=24h
```

### 推奨モデル構成
| 役割 | モデル | 量子化 | 推定VRAM |
|------|--------|--------|----------|
| Planner/Writer | deepseek-r1:7b | Q4_K_M | ~5.4GB |
| Worker | qwen2.5:3b | Q4_K_M | ~2.5GB |

※ 同時実行ではなく、切り替えて使用

---

## 実装優先度

| 優先度 | フェーズ | 理由 | 状態 |
|--------|----------|------|------|
| P0 | フェーズ1 | 基盤なしには何も動かない | ✅ 完了 |
| P0 | フェーズ2 | プロジェクト構造の確立 | ✅ 完了 |
| P1 | フェーズ3 | コア機能の実装 | ✅ 完了 |
| P1 | フェーズ4 | ノードの実装 | ✅ 完了 |
| P1 | フェーズ5 | 統合 | 📝 スタブ |
| P2 | フェーズ6 | 品質向上 | ⏳ 未着手 |
| P3 | フェーズ7 | 仕上げ | ⏳ 未着手 |

---

## 次のアクション

~~1. `docker-compose.yaml`の作成とDocker環境の起動~~ ✅ 完了
~~2. SearXNGの設定とAPI動作確認~~ ✅ 完了
~~3. Ollamaでのモデルプルとテスト推論~~ ✅ 完了

**フェーズ3-4 完了:**
~~1. `tools/search.py` の TDD 実装~~ ✅ 完了
~~2. `tools/scrape.py` の TDD 実装~~ ✅ 完了
~~3. `prompts/templates.py` のテスト作成~~ ✅ 完了
~~4. デモモードの実装~~ ✅ 完了
~~5. `llm.py` の TDD 実装~~ ✅ 完了
~~6. 各ノード（`nodes/*.py`）の TDD 実装~~ ✅ 完了

**フェーズ5 完了:**
~~1. `graph.py` の TDD 実装（StateGraph構築）~~ ✅ 完了
~~2. ノード間のエッジ定義~~ ✅ 完了
~~3. `should_continue_research` による条件付きルーティング~~ ✅ 完了
~~4. 統合テストの作成~~ ✅ 完了
~~5. `main.py` のフル実行モード実装~~ ✅ 完了

**現在の次のステップ（フェーズ6）:**
1. Docker環境での実際のエンドツーエンドテスト
2. VRAM使用量の計測と最適化
3. エラーハンドリングの強化
4. 統合テストスイートの拡充

**実行コマンド:**
```bash
# フル研究実行
uv run python -m src.main "リサーチトピック"

# ファイル出力付き
uv run python -m src.main --output report.md "リサーチトピック"

# デモモード
uv run python -m src.main --demo search "Python programming"
uv run python -m src.main --demo scrape "https://example.com"
uv run python -m src.main --demo plan "量子コンピュータとは何か"
uv run python -m src.main --demo summarize "長いテキスト..."
```

---

*この計画はinitial-plan.mdの技術仕様に基づいて作成されました。実装中に発見された課題に応じて更新される可能性があります。*
