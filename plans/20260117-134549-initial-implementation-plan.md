# ローカルDeep Researchシステム 実装計画

**作成日**: 2026-01-17
**ベースドキュメント**: [initial-plan.md](initial-plan.md)

---

## 概要

GTX 1660 SUPER（6GB VRAM）環境で動作する自律型Deep Researchエージェントを構築する。LangGraphを用いたグラフベースのワークフロー、Ollamaによるローカル推論、SearXNGによるプライバシー重視の検索、Crawl4AIによるスクレイピングを組み合わせる。

---

## フェーズ1: 基盤環境の構築

### 1.1 Docker環境のセットアップ
- [ ] NVIDIA Container Toolkitのインストール確認
- [ ] `docker-compose.yaml`の作成
  - Ollamaサービス（GPU対応、Flash Attention有効化）
  - SearXNGサービス（メタ検索エンジン）
- [ ] SearXNG設定ファイルの作成（`searxng/settings.yml`）
  - 使用する検索エンジンの選定（Google, Bing, DuckDuckGo等）
  - JSON API出力の有効化

### 1.2 モデルの準備
- [ ] Plannerモデル: `deepseek-r1:7b`のプル
- [ ] Workerモデル: `qwen2.5:3b`のプル
- [ ] 各モデルのVRAM使用量検証

**成果物**:
- `docker-compose.yaml`
- `searxng/settings.yml`
- 動作確認済みのOllama + SearXNG環境

---

## フェーズ2: Pythonプロジェクト構造の構築

### 2.1 プロジェクト初期化
- [ ] `pyproject.toml`または`requirements.txt`の作成
- [ ] 仮想環境のセットアップ（uv, poetry, または venv）

### 2.2 依存ライブラリ
```
langgraph
langchain-ollama
crawl4ai
aiohttp
pydantic
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

### 3.1 設定管理 (`config.py`)
- [ ] Ollamaエンドポイント設定
- [ ] SearXNGエンドポイント設定
- [ ] モデル名の定義（Planner/Worker）
- [ ] コンテキスト長制限の設定

### 3.2 状態定義 (`state.py`)
- [ ] `ResearchState` TypedDictの実装
  - `task`: ユーザーの元の質問
  - `plan`: 検索計画（サブクエリリスト）
  - `steps_completed`: 実行ステップ数
  - `content`: 要約済み情報リスト（Annotated + operator.add）
  - `current_search_query`: 現在のクエリ
  - `references`: 引用元URLリスト
  - `is_sufficient`: 情報充足フラグ

### 3.3 ツール実装

#### 3.3.1 検索ツール (`tools/search.py`)
- [ ] SearXNG APIクライアントの実装
- [ ] 検索結果のパース（タイトル、URL、スニペット）
- [ ] エラーハンドリング

#### 3.3.2 スクレイピングツール (`tools/scrape.py`)
- [ ] Crawl4AIの初期化と設定
- [ ] Markdown変換機能の利用
- [ ] メモリ管理（1ページずつ順次処理）
- [ ] タイムアウト・エラーハンドリング

### 3.4 プロンプトテンプレート (`prompts/templates.py`)
- [ ] Planner用プロンプト（JSON出力強制）
- [ ] Summarizer用プロンプト
- [ ] Reviewer用プロンプト（情報充足判定）
- [ ] Writer用プロンプト（レポート生成）

**成果物**:
- 設定管理モジュール
- 状態定義
- 検索・スクレイピングツール
- プロンプトテンプレート集

---

## フェーズ4: LangGraphノードの実装

### 4.1 Plannerノード (`nodes/planner.py`)
- [ ] DeepSeek R1モデルの呼び出し
- [ ] ユーザー入力からサブクエリへの分解
- [ ] JSON出力のパースとバリデーション
- [ ] パース失敗時のリトライロジック

### 4.2 Researcherノード (`nodes/researcher.py`)
- [ ] 計画に基づく検索クエリの発行
- [ ] SearXNGツールの呼び出し
- [ ] URLリストの状態への保存

### 4.3 Scraper & Summarizerノード (`nodes/scraper.py`)
- [ ] URLからのコンテンツ取得（Crawl4AI）
- [ ] Workerモデル（Qwen 2.5 3B）による即時要約
- [ ] 要約結果の状態への追加
- [ ] 参照URLの記録

### 4.4 Reviewerノード (`nodes/reviewer.py`)
- [ ] 収集情報の充足度判定
- [ ] 不足時: Researcherへの戻り指示
- [ ] 充足時: Writerへの進行指示

### 4.5 Writerノード (`nodes/writer.py`)
- [ ] 蓄積情報の統合
- [ ] 最終レポートの生成（DeepSeek R1使用）
- [ ] 引用元URLの明記

**成果物**:
- 全5ノードの実装

---

## フェーズ5: グラフの構築と統合

### 5.1 グラフ定義 (`graph.py`)
- [ ] StateGraphの初期化
- [ ] 各ノードの追加
- [ ] エッジ（遷移）の定義
  - START → Planner
  - Planner → Researcher
  - Researcher → Scraper
  - Scraper → Reviewer
  - Reviewer → Researcher（ループ）または Writer
  - Writer → END
- [ ] 条件付きエッジの実装（Reviewer判定による分岐）

### 5.2 グラフのコンパイルと実行
- [ ] グラフのコンパイル
- [ ] 入力・出力インターフェースの定義

### 5.3 エントリーポイント (`main.py`)
- [ ] CLIインターフェースの実装
- [ ] 非同期実行のセットアップ
- [ ] 結果の出力（Markdown形式）

**成果物**:
- 完成したLangGraphワークフロー
- 実行可能なCLIアプリケーション

---

## フェーズ6: 最適化とテスト

### 6.1 VRAM最適化
- [ ] 実際のメモリ使用量の計測
- [ ] コンテキスト長の調整
- [ ] モデル切り替えのバッチ化検討

### 6.2 エラーハンドリング強化
- [ ] ネットワークエラーのリトライ
- [ ] モデル出力のバリデーション
- [ ] タイムアウト処理

### 6.3 テスト
- [ ] 単体テスト（各ツール、各ノード）
- [ ] 統合テスト（エンドツーエンド）
- [ ] パフォーマンステスト（処理時間、メモリ使用量）

**成果物**:
- テストスイート
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

| 優先度 | フェーズ | 理由 |
|--------|----------|------|
| P0 | フェーズ1 | 基盤なしには何も動かない |
| P0 | フェーズ2 | プロジェクト構造の確立 |
| P1 | フェーズ3 | コア機能の実装 |
| P1 | フェーズ4 | ノードの実装 |
| P1 | フェーズ5 | 統合 |
| P2 | フェーズ6 | 品質向上 |
| P3 | フェーズ7 | 仕上げ |

---

## 次のアクション

1. `docker-compose.yaml`の作成とDocker環境の起動
2. SearXNGの設定とAPI動作確認
3. Ollamaでのモデルプルとテスト推論

---

*この計画はinitial-plan.mdの技術仕様に基づいて作成されました。実装中に発見された課題に応じて更新される可能性があります。*
