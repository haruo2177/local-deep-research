# リサーチ品質ガードレール強化 実装計画

**作成日**: 2026-02-07  
**目的**: `ゆる言語学ラジオ` のような明確なユーザー意図に対し、検索逸脱・言語逸脱・品質未達のまま完了する問題を解消する。

---

## 背景
- 実行ログ上、Plannerのクエリ品質低下により無関係URLが大量混入し、要約・レビュー・最終執筆までノイズが伝播している。
- Reviewerが不十分判定でも `max_iterations` 到達で強制終了し、品質未達レポートが確定する。
- Reviewer応答がJSONコードフェンス等を含むとパースに失敗し、`sufficient=true` 相当の応答でも `False` 扱いになる。
- 日本語入力にもかかわらず最終出力が中国語になり、出力言語ポリシーが破綻している。
- `chars=1` の実質空コンテンツ（ログイン壁/ボット対策ページ等）まで要約対象になり、レビュー入力にノイズが蓄積する。
- 一部要約呼び出しが極端に長時間化し、スクレイプ・要約が逐次実行のため全体時間を圧迫している。

## ゴール
- 検索結果の関連性を改善し、タスクとの無関係URL流入を大幅に削減する。
- 出力言語を入力言語（少なくとも `ja`）に一致させる。
- 品質未達時に「強制完了」ではなく、理由つき終了または追加探索に遷移させる。
- Reviewer判定のJSONパース耐性を上げ、誤判定による無駄ループを防止する。
- LLM要約の異常長時間化を抑止し、総実行時間を短縮する。

## 非ゴール
- 外部検索エンジンやモデル自体の入れ替え。
- UI/CLI仕様の全面変更。

---

## 実装優先順位

### 1. Plannerクエリ品質ゲート
**対象**: `src/nodes/planner.py`, `src/prompts/templates.py`, `tests/nodes/test_planner.py`

- クエリ正規化を追加（全角半角・空白・言語混在の最小正規化）。
- タスク由来キーワードの最低含有条件を導入（例: 固有語を1語以上）。
- 禁止パターン（無関係語、文字化け/異言語ノイズ）を除外。
- 品質閾値未達時は再生成（最大再試行回数を制限）。

**完了条件**
- 明らかに無関係なクエリ（例: 韓国語混在の誤語）が生成されない。
- Plannerテストに品質ゲートのユースケースを追加し、再現ログ相当ケースが通る。

### 2. URL関連性フィルタ（Scraper前）
**対象**: `src/nodes/researcher.py`, `src/tools/search.py`, `tests/nodes/test_researcher.py`, `tests/tools/test_search.py`

- URL候補に関連性スコアを導入（タイトル/スニペットのタスク語一致率 + ドメイン健全性）。
- SearXNG問い合わせに言語/セーフサーチ/カテゴリ等の基本パラメータ制約を導入し、候補母集団のノイズを削減。
- 低スコアURLを除外し、同一コンテンツ重複（`youtube.com` と `m.youtube.com` など）を統合。
- 各ステップで「採用/除外理由」をINFOログ出力。

**完了条件**
- 無関係ドメインの採用率が有意に低下する。
- 重複URLの採用が抑制される。

### 3. 出力言語ポリシー固定
**対象**: `src/nodes/writer.py`, `src/nodes/translator.py`, `src/prompts/templates.py`, `tests/nodes/test_writer.py`, `tests/nodes/test_translator.py`

- Writerプロンプトに「出力言語=source_language」を明示。
- 最終出力の言語検出で不一致なら再生成、または強制翻訳フォールバック。
- 「英語以外は翻訳しない」分岐を、入力言語整合優先の分岐に改修。

**完了条件**
- 日本語タスク入力時、最終レポートが日本語で返る。
- 中国語/英語誤出力の再現ケースがテストで失敗しなくなる。

### 4. Scraper入力品質ゲート
**対象**: `src/nodes/scraper.py`, `src/tools/scrape.py`, `tests/nodes/test_scraper.py`, `tests/tools/test_scrape.py`

- 最小本文長閾値（例: 200文字）を導入し、短すぎるページを要約対象から除外。
- 既知の取得失敗パターン（ログイン要求、CAPTCHA、`Please provide the content...` 誘導文）を検知して除外。
- `content` へ格納する前に「有効要約か」を検証し、無効要約をレビュー入力に渡さない。

**完了条件**
- `chars=1` 相当ページが要約・レビューへ流入しない。
- 要約不能URLがあっても、最終レポート品質を不必要に劣化させない。

### 5. LLM要約/執筆のタイムアウト・並列化・コンテキスト予算制御
**対象**: `src/llm.py`, `src/nodes/scraper.py`, `src/nodes/writer.py`, `src/config.py`, `tests/test_llm.py`, `tests/nodes/test_scraper.py`, `tests/nodes/test_writer.py`

- 要約用途の呼び出しに時間上限・最大トークン上限を設定。
- 異常応答（過剰長文、命令文応答）の簡易検知を追加し、1回だけ再試行。
- リトライ後も異常なら「要約失敗」として次URLに進む。
- スクレイプ/要約の並列度を制御可能にし、逐次処理を解消（例: セマフォで2-3並列）。
- Writer入力の要約再圧縮とサイズ上限を導入し、巨大プロンプト投入を回避（`max_context_length` を実効利用）。

**完了条件**
- 1件の要約で数百秒ブロックしない。
- 異常出力が最終レビュー入力に残りにくくなる。
- 総処理時間（同条件実行）が有意に短縮する。

### 6. Reviewer終了条件とJSONパース耐性の改修
**対象**: `src/nodes/reviewer.py`, `src/graph.py`, `src/state.py`, `tests/nodes/test_reviewer.py`, `tests/test_graph.py`, `tests/integration/test_workflow.py`

- `max_iterations` 到達時の強制 `sufficient=True` を廃止。
- Reviewer応答からJSON本体を抽出するフォールバック（コードフェンス除去、先頭JSON抽出）を追加。
- 未達時は「不足理由つき終了」または「不足点ベース追加検索」のいずれかに遷移。
- 失敗終了時も利用可能な中間成果と不足点を返却。

**完了条件**
- 品質未達のまま成功扱いにならない。
- `sufficient=true` を含む応答がフォーマット揺れで取りこぼされない。
- 失敗時の説明可能性（不足理由）が担保される。

---

## 実装順序（推奨）
1. Plannerクエリ品質ゲート  
2. URL関連性フィルタ  
3. 出力言語ポリシー固定  
4. Scraper入力品質ゲート  
5. LLM要約/執筆のタイムアウト・並列化・コンテキスト予算制御  
6. Reviewer終了条件とJSONパース耐性の改修

---

## Issue分割（実装タスク）

### QG-01 Plannerクエリ品質ゲート
**目的**: 検索クエリの言語/固有語/ノイズ混入を制御し、初期探索の精度を上げる。  
**主変更**: `src/nodes/planner.py`, `src/prompts/templates.py`, `tests/nodes/test_planner.py`  
**作業項目**
- クエリ正規化・品質チェック関数の実装（最小語数、固有語含有、言語混在抑制）。
- 低品質時の再生成ループ（上限回数あり）を追加。
- 採用/棄却理由のログを追加。  
**受け入れ基準**
- `ゆる言語学ラジオ` 入力で、明らかな無関係語や多言語混在クエリが採用されない。  
**テスト**
- `tests/nodes/test_planner.py` に品質ゲート成功/失敗/再試行ケースを追加。

### QG-02 URL関連性フィルタ（Researcher/Search）
**目的**: 検索結果から無関係ドメインを早期除外し、Scraperへのノイズ流入を抑える。  
**主変更**: `src/nodes/researcher.py`, `src/tools/search.py`, `tests/nodes/test_researcher.py`, `tests/tools/test_search.py`  
**作業項目**
- タイトル/スニペット/URLを使った関連度スコアリングを実装。
- SearXNGクエリに言語・カテゴリ等の基本制約を追加。
- URL正規化で重複統合（`www`/`m.` 差分等）。  
**受け入れ基準**
- 同一入力で無関係ドメイン採用率が導入前より低下。  
**テスト**
- 低関連度URL除外、重複URL統合、制約付き検索パラメータの単体テストを追加。

### QG-03 出力言語ポリシー固定
**目的**: 最終レポート言語を入力言語に一致させる。  
**主変更**: `src/nodes/writer.py`, `src/nodes/translator.py`, `src/prompts/templates.py`, `tests/nodes/test_writer.py`, `tests/nodes/test_translator.py`  
**作業項目**
- Writerプロンプトに目標言語を明示的に埋め込む。
- 出力言語検証を追加し、不一致時は再生成または翻訳フォールバック。
- `translator_output` の「英語のみ翻訳」前提を廃止し、入力言語整合優先へ変更。  
**受け入れ基準**
- 日本語入力で最終出力が日本語になる（中国語/英語で終わらない）。  
**テスト**
- 言語不一致時の再生成/翻訳フォールバックのテストを追加。

### QG-04 Scraper入力品質ゲート
**目的**: 取得失敗ページや実質空コンテンツを要約対象から除外する。  
**主変更**: `src/nodes/scraper.py`, `src/tools/scrape.py`, `tests/nodes/test_scraper.py`, `tests/tools/test_scrape.py`  
**作業項目**
- 最小本文長閾値と失敗パターン判定（ログイン壁/CAPTCHA等）を追加。
- 要約結果に対する簡易バリデーション（指示文応答・空洞要約除外）を追加。
- 除外理由を観測可能なログ/メトリクスへ出力。  
**受け入れ基準**
- `chars=1` 相当ページが `content` に格納されない。  
**テスト**
- 短文ページ・壁ページ・無効要約の除外ケースを追加。

### QG-05 LLM呼び出し最適化（時間/並列/コンテキスト）
**目的**: 総処理時間を短縮し、長時間ブロックと巨大プロンプトを抑止する。  
**主変更**: `src/llm.py`, `src/nodes/scraper.py`, `src/nodes/writer.py`, `src/config.py`, `tests/test_llm.py`, `tests/nodes/test_scraper.py`, `tests/nodes/test_writer.py`  
**作業項目**
- 要約/執筆ごとのタイムアウト・最大生成量設定を追加。
- Scraper内の要約処理を並列化（セマフォで同時実行数制御）。
- Writer前に内容圧縮を実施し、`max_context_length` に沿った入力予算を適用。  
**受け入れ基準**
- 同条件実行で総時間が短縮し、単一要約の極端な長時間化が抑制される。  
**テスト**
- タイムアウト、並列度、プロンプト圧縮の単体テストを追加。

### QG-06 Reviewer判定の堅牢化（終了条件+JSONパース）
**目的**: フォーマット揺れによる誤判定と、`max_iterations` 強制成功を解消する。  
**主変更**: `src/nodes/reviewer.py`, `src/graph.py`, `src/state.py`, `tests/nodes/test_reviewer.py`, `tests/test_graph.py`, `tests/integration/test_workflow.py`  
**作業項目**
- コードフェンス除去・JSON抽出フォールバックを実装。
- `max_iterations` 到達時の強制 `sufficient=True` を撤廃。
- 不足理由つき終了経路、または不足点ベース再探索経路を実装。  
**受け入れ基準**
- `{"sufficient": true}` を含む応答を取りこぼさない。
- 品質未達のまま成功終了しない。  
**テスト**
- JSON揺れケース、最大反復到達時の終了分岐、統合ワークフロー回帰を追加。

### QG-07 計測・検証整備（横断）
**目的**: 改修効果を定量評価し、劣化を早期検知する。  
**主変更**: `src/main.py`, 各ノードのログ出力、必要に応じ `tests/integration/*`  
**作業項目**
- 新規メトリクス（`scrape_low_content_skip_count` 等）を集計・表示。
- 代表入力（`ゆる言語学ラジオ`）でベースライン比較手順を整備。
- READMEまたは運用ドキュメントへ検証手順を追記。  
**受け入れ基準**
- 主要指標（関連率、言語一致、強制成功0、実行時間）が1回の実行ログで確認可能。  
**テスト**
- 可能な範囲でメトリクス集計の単体/統合テストを追加。

### 依存関係
- QG-01 → QG-02（クエリ品質がURL品質に影響）
- QG-02 → QG-04（前段フィルタ後にScraper品質ゲート）
- QG-03 は QG-05/QG-06 と並行可能
- QG-06 は QG-07 前に完了（強制成功0を計測可能にするため）

### マイルストーン（推奨）
1. M1: QG-01, QG-02 完了（探索精度の土台）  
2. M2: QG-03, QG-04 完了（言語整合とノイズ抑制）  
3. M3: QG-05, QG-06 完了（速度・終了品質）  
4. M4: QG-07 完了（計測確立、回帰確認）

---

## 追補（2026-02-07 17:47 実行ログ反映）

### 追加で確認された失敗モード
- Reviewerが ```json ... ``` 形式を返しても `sufficient=False` になる（JSONパース失敗の再現）。
- `max_iterations=5` 到達で強制 `sufficient=True` となり、品質未達のままWriterへ遷移する。
- 要約結果として `<unused...>`、1文字出力、指示文応答（`Please provide...`）が `content` に混入する。
- オフトピックURL（例: X/Twitter, Zhihu, 無関係ニュース）が継続的に採用され、最終レポート主題が逸脱する。
- 最終翻訳で意味崩壊（英語レポート -> 不自然な日本語1文）が発生する。

### ホットフィックス優先順（順序を前倒し）
1. **QG-06 先行実装**: ReviewerのJSON抽出フォールバック + 強制成功廃止  
2. **QG-04 先行実装**: 要約採用前の品質ゲート（`<unused>`, 極短文, 指示文応答を破棄）  
3. **QG-03 部分先行**: 出力言語不一致時の「翻訳」より「同言語再生成」を優先  
4. QG-02 を続行してURLノイズ流入を低減  
5. QG-05 で速度最適化（並列化・タイムアウト）

### 受け入れ基準の追記（必須）
- Reviewer:
  - コードフェンス付きJSON応答で `sufficient=true` を正しく解釈できること。
  - `max_iterations` 到達時に成功扱いへ自動昇格しないこと。
- Scraper:
  - 以下を `content` に格納しないこと: `<unused...>`, 文字数閾値未満, 指示要求文（例: `Please provide...`）。
  - 要約言語がタスク言語と不一致の場合は破棄または再要約すること。
- Translator/Writer:
  - 日本語入力時、最終出力が自然な日本語段落で返ること（単文崩壊を不可）。
  - 翻訳品質が閾値未満の場合は翻訳結果を採用せず、Writer再生成へフォールバックすること。
- End-to-end:
  - `ゆる言語学ラジオ` 実行で主題逸脱（X/Zhihu中心レポート）を許容しないこと。

### 追加メトリクス
- `summary_invalid_output_drop_count`: `<unused>`・指示文・極短文などで破棄した要約件数
- `reviewer_parse_error_count`: Reviewer応答のJSON抽出失敗回数
- `forced_success_count`: 強制成功回数（改修後は常時0）
- `offtopic_reference_ratio`: 参照URL中の非関連ドメイン比率
- `translation_quality_fallback_count`: 翻訳結果を破棄して再生成へ切り替えた回数

---

## テスト戦略
- 単体テスト: ノード単位で異常ケースを固定再現（無関係クエリ、異言語出力、長時間要約）。
- 統合テスト: `ゆる言語学ラジオ` に近い日本語タスクで、関連URL比率・出力言語・終了条件を検証。
- 回帰テスト: 既存の正常系（短い英語タスク等）が壊れていないことを確認。

### 実行コマンド
```bash
uv run pytest -q
```

---

## 計測指標（導入後）
- `relevance_accept_rate`: 候補URLに対する採用率
- `offtopic_reject_count`: 無関係URL除外数
- `output_language_match`: 入力言語と最終出力言語の一致率
- `summary_timeout_count`: 要約タイムアウト件数
- `scrape_low_content_skip_count`: 低品質（短文/壁ページ）除外件数
- `reviewer_json_parse_fallback_count`: Reviewerパースフォールバック発動件数
- `writer_prompt_chars`: Writer投入プロンプト文字数（閾値超過率を監視）
- `forced_success_count`: 強制成功件数（改修後は0を維持）

---

## リスクと対策
- フィルタが厳しすぎて情報不足になるリスク: 閾値を段階的に調整し、最低採用件数を確保。
- 再試行増で遅延が増えるリスク: 再試行回数を用途別に上限固定。
- 言語検出誤判定リスク: 短文時は検出信頼度閾値を設け、低信頼時は翻訳フォールバック優先。
