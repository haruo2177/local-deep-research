# Phase 5: グラフ構築と統合 - 実装ログ

**日時**: 2026-01-18
**フェーズ**: 5

---

## 完了タスク

### グラフ構築（初期実装）

- [x] `tests/test_graph.py` を作成（14テスト）
  - グラフ構築テスト（3テスト）
  - エッジ定義テスト（6テスト）
  - 条件付きルーティングテスト（3テスト）
  - 統合テスト（2テスト）
- [x] `src/graph.py` を実装
  - StateGraph初期化
  - 5ノード（planner, researcher, scraper, reviewer, writer）の登録
  - エッジ定義（START → Planner → Researcher → Scraper → Reviewer）
  - 条件付きエッジ（Reviewer → Writer または Researcher）
  - グラフコンパイル
- [x] `src/state.py` に `report` フィールドを追加
- [x] `tests/test_main.py` にフル実行モードテストを追加（4テスト）
- [x] `src/main.py` を更新
  - `run_research()` 関数追加
  - `--output` フラグ対応
  - フル研究実行モード実装

### バグ修正: 重複URLスクレイピング

実行ログから同じURLが複数回スクレイピングされる問題を発見・修正。

- [x] `src/state.py`: `scraped_urls: Annotated[list[str], operator.add]` フィールドを追加
- [x] `src/nodes/scraper.py`: 既にスクレイピング済みのURLをスキップするロジックを追加
- [x] `src/main.py`: 初期状態に `scraped_urls: []` を追加
- [x] `tests/nodes/test_scraper.py`: 2テスト追加
  - `test_scraper_returns_scraped_urls`
  - `test_scraper_skips_already_scraped_urls`
- [x] `tests/test_graph.py`: モックノードに `scraped_urls` 対応を追加

### 改善: 最小イテレーション数の追加

リサーチ量が少ない問題に対応し、最低2回のリサーチサイクルを保証。

- [x] `src/nodes/reviewer.py`: `MIN_ITERATIONS = 2` を追加
  - `steps_completed < MIN_ITERATIONS` の場合は LLM を呼ばずに `is_sufficient=False` を返す
- [x] `tests/nodes/test_reviewer.py`: テスト更新
  - `steps_completed` を 2 以上に変更
  - `test_reviewer_forces_false_below_min_iterations` テストを追加

---

## TDD記録

### テスト作成（Red）
1. `test_graph.py`: 14テスト作成 → 全て失敗（`NotImplementedError`）
2. `test_main.py`: 4テスト追加 → 全て失敗（`ImportError: run_research`）

### 実装（Green）
1. `src/graph.py`: StateGraphとエッジを実装 → 12テスト通過
2. `src/state.py`: `report` フィールド追加 → 14テスト通過
3. `src/main.py`: `run_research()` 追加 → 全テスト通過

### リファクタリング
- LangGraph型システム互換性のため `# type: ignore[type-var]` を追加
- インポート順序とコードスタイルを修正

---

## テスト結果

```
137 passed in 1.58s
Coverage: 95%
mypy: Success: no issues found
ruff: All checks passed!
```

---

## 新規作成/変更ファイル

| ファイル | アクション |
|---------|-----------|
| `tests/test_graph.py` | 新規作成（14テスト） |
| `src/graph.py` | 実装完了 |
| `src/state.py` | `report` + `scraped_urls` フィールド追加 |
| `tests/test_main.py` | テスト追加（4テスト） |
| `src/main.py` | フル実行モード実装、初期状態に `scraped_urls` 追加 |
| `src/nodes/scraper.py` | 重複URLスキップ機能追加 |
| `src/nodes/reviewer.py` | `MIN_ITERATIONS = 2` 追加 |
| `tests/nodes/test_scraper.py` | 2テスト追加 |
| `tests/nodes/test_reviewer.py` | テスト更新、1テスト追加 |
| `src/prompts/templates.py` | 言語指示を削除（シンプル化） |

---

## グラフワークフロー

```
START → Planner → Researcher → Scraper → Reviewer ─┬─► Writer → END
                     ▲                              │
                     └───── 情報不十分 ─────────────┘
```

---

## 使用方法

```bash
# フル研究実行
uv run python -m src.main "リサーチトピック"

# ファイル出力付き
uv run python -m src.main --output report.md "リサーチトピック"

# デモモード（従来通り）
uv run python -m src.main --demo search "Python programming"
uv run python -m src.main --demo plan "量子コンピュータとは"
```

---

## 次回への引き継ぎ

### 完了
- Phase 5（グラフ構築と統合）完了
- 全ノードがLangGraphで接続された状態
- 重複URLスクレイピング問題を修正（`scraped_urls` で追跡）
- 最小イテレーション数（MIN_ITERATIONS=2）を追加
- ドキュメント更新（README.md、実装計画）

### 次のステップ（Phase 6）
- [ ] Docker環境での実際のエンドツーエンドテスト
- [ ] VRAM使用量の計測と最適化
- [ ] エラーハンドリングの強化
- [ ] 統合テストスイートの拡充

### 確認事項
- Docker環境（Ollama + SearXNG）を起動して手動テストを実施すること
- 実際のLLMレスポンスでのフロー確認が必要
- MIN_ITERATIONS=2 により、最低2回のリサーチサイクルが実行される
