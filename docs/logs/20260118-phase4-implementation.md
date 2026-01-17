# 実装ログ: Phase 4 LangGraphノード実装

**日時**: 2026-01-18

## 目標

Phase 4として、5つのLangGraphノードとLLMユーティリティをTDDで実装する。

## 完了タスク

- [x] src/llm.py: LLM呼び出しユーティリティ
- [x] src/nodes/planner.py: 検索クエリ生成ノード
- [x] src/nodes/researcher.py: SearXNG検索実行ノード
- [x] src/nodes/scraper.py: コンテンツ取得・要約ノード
- [x] src/nodes/reviewer.py: 情報充足性判定ノード
- [x] src/nodes/writer.py: 最終レポート生成ノード
- [x] src/main.py: デモモード拡張（plan, summarize追加）
- [x] src/prompts/templates.py: PLANNER_PROMPT改善

---

## やり取りの記録

### 1. LLMユーティリティ実装

`src/llm.py`を作成。`call_llm`関数と`LLMError`例外クラスを実装。langchain_ollamaのChatOllamaを使用。

### 2. ノード実装（TDD）

各ノードをRed→Green→Refactorサイクルで実装。モックを使用してLLM呼び出しをテスト。

### 3. デモモード拡張

`--demo plan`と`--demo summarize`を追加し、Phase 4の動作確認が可能に。

### 4. プロンプト改善

PLANNER_PROMPTを改善し、キーワード形式のクエリ生成を指示。ただしDeepSeek R1:7bの特性上、完全なキーワード形式にはならない。

---

## TDD記録

### llm.py

1. RED: tests/test_llm.py作成 → ModuleNotFoundError
2. GREEN: src/llm.py実装 → テストパス
3. 結果: 7テスト PASS

**テスト内容:**
- call_llm_returns_string
- call_llm_uses_specified_model
- call_llm_default_model
- call_llm_handles_timeout
- call_llm_handles_connection_error
- llm_error_is_exception
- llm_error_message

### nodes/planner.py

1. RED: tests/nodes/test_planner.py作成 → AttributeError
2. GREEN: src/nodes/planner.py実装 → テストパス
3. 結果: 11テスト PASS

**テスト内容:**
- planner_returns_plan_list
- planner_parses_json_response
- planner_retries_on_invalid_json
- planner_max_retries_exceeded
- planner_uses_task_as_fallback
- planner_calls_correct_model
- planner_handles_llm_error
- planner_empty_task_raises
- planner_whitespace_task_raises
- planner_error_is_exception
- planner_error_message

### nodes/researcher.py

1. RED: tests/nodes/test_researcher.py作成 → AttributeError
2. GREEN: src/nodes/researcher.py実装 → テストパス
3. 結果: 8テスト PASS

**テスト内容:**
- researcher_executes_current_query
- researcher_extracts_urls
- researcher_limits_results
- researcher_increments_steps
- researcher_handles_empty_results
- researcher_handles_search_error
- researcher_skips_duplicate_urls
- researcher_returns_current_search_query

### nodes/scraper.py

1. RED: tests/nodes/test_scraper.py作成 → AttributeError
2. GREEN: src/nodes/scraper.py実装 → テストパス
3. 結果: 8テスト PASS

**テスト内容:**
- scraper_fetches_urls
- scraper_summarizes_content
- scraper_uses_worker_model
- scraper_handles_scrape_failure
- scraper_truncates_long_content
- scraper_returns_content_list
- scraper_handles_empty_urls
- scraper_includes_source_in_summary

### nodes/reviewer.py

1. RED: tests/nodes/test_reviewer.py作成 → AttributeError
2. GREEN: src/nodes/reviewer.py実装 → テストパス
3. 結果: 9テスト PASS

**テスト内容:**
- reviewer_returns_is_sufficient
- reviewer_sufficient_true
- reviewer_sufficient_false
- reviewer_max_iterations_forces_true
- reviewer_parses_json_response
- reviewer_handles_invalid_json
- reviewer_uses_worker_model
- should_continue_returns_writer
- should_continue_returns_researcher

### nodes/writer.py

1. RED: tests/nodes/test_writer.py作成 → AttributeError
2. GREEN: src/nodes/writer.py実装 → テストパス
3. 結果: 8テスト PASS

**テスト内容:**
- writer_returns_report
- writer_uses_planner_model
- writer_includes_all_content
- writer_formats_references
- writer_handles_empty_content
- writer_handles_llm_error
- writer_error_is_exception
- writer_error_message

### main.py（デモモード拡張）

1. RED: tests/test_main.pyに追加 → テスト失敗
2. GREEN: src/main.pyにdemo_plan, demo_summarize追加 → テストパス
3. 結果: 6テスト PASS（+2追加）

---

## 問題と解決策

### 1. ruff B904: 例外チェーンエラー

**発生箇所**: src/nodes/planner.py:51-55

**エラー内容**:
```
B904 Within an `except` clause, raise exceptions with `raise ... from err`
```

**原因**:
except句内でraiseする際に、元の例外を連鎖させていなかった。

**解決策**:
```python
# 修正前
except json.JSONDecodeError:
    raise PlannerError("Failed to parse JSON")

# 修正後
except json.JSONDecodeError as e:
    raise PlannerError("Failed to parse JSON") from e
```

### 2. mypy: Returning Any from function

**発生箇所**: src/nodes/planner.py:75

**エラー内容**:
```
error: Returning Any from function declared to return "list[str]"
```

**原因**:
`data.get("queries", [])`がAny型を返すため。

**解決策**:
```python
# 修正前
queries = data.get("queries", [])

# 修正後
queries: list[str] = data.get("queries", [])
```

### 3. PLANNER_PROMPTの出力形式

**発生箇所**: src/prompts/templates.py

**問題**:
LLMが文章形式のクエリを生成（「量子コンピュータの定義」など）

**原因**:
DeepSeek R1:7bは小型モデルのため、細かい形式指示に完全に従いにくい。

**解決策**:
プロンプトを改善したが、完全なキーワード形式にはならない。検索エンジンは文章形式でも動作するため、Phase 5で必要に応じて再チューニング。

---

## 品質チェック結果

```
pytest: 116 passed
coverage: 95%
mypy: Success: no issues found in 17 source files
ruff check: All checks passed!
ruff format: 34 files already formatted
```

---

## 作成/変更ファイル一覧

```
src/llm.py                      # 新規
src/nodes/planner.py            # 実装
src/nodes/researcher.py         # 実装
src/nodes/scraper.py            # 実装
src/nodes/reviewer.py           # 実装
src/nodes/writer.py             # 実装
src/main.py                     # デモモード拡張
src/prompts/templates.py        # PLANNER_PROMPT改善
tests/test_llm.py               # 新規
tests/nodes/test_planner.py     # 新規
tests/nodes/test_researcher.py  # 新規
tests/nodes/test_scraper.py     # 新規
tests/nodes/test_reviewer.py    # 新規
tests/nodes/test_writer.py      # 新規
tests/test_main.py              # 追加テスト
```

---

## Git操作

```
コミット: e3c8065 Phase 4: LangGraphノード実装（TDD）
プッシュ: 82ea487..e3c8065 main -> main
```

---

## 学んだこと

- TDDサイクルでモックを活用することで、外部依存（LLM）なしでロジックをテスト可能
- ruffのB904ルールは例外チェーンの適切な使用を強制する
- 小型LLMはプロンプト指示に完全に従いにくいが、実用上は問題ないことが多い

---

## 次回への引き継ぎ

- [ ] Phase 5: グラフ構築（src/graph.py）
- [ ] ノード間の接続とエッジ設定
- [ ] should_continue_researchによる条件付きルーティング
- [ ] 統合テストの作成

---

## 参考リンク

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [実装計画](../plans/20260117-212457-phase3.4-4-implementation.md)
