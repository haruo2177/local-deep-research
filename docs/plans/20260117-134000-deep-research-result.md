# **ローカル環境における自律型Deep Researchシステムの構築：GTX 1660 SUPERを用いた制約下での最適化と実装戦略**

## **1\. 序論：制約下における自律型研究エージェントの可能性**

生成AI技術の急速な進化により、単なるチャットボットを超えた「自律型エージェント」の構築が現実的なものとなりつつあります。特に、与えられたテーマに対して自ら検索計画を立案し、ウェブ上の情報を収集・分析し、包括的なレポートを作成する「Deep Research（深層研究）」システムは、知的生産性を飛躍的に向上させるアプリケーションとして注目を集めています。OpenAIのDeep ResearchやDeepSeekの推論モデルなどがその代表例ですが、これらは通常、大規模なクラウドインフラストラクチャ上で動作する巨大なモデルに依存しています 1。

しかし、プライバシー保護、コスト削減、そして技術的な自律性の観点から、これらのシステムをローカル環境で構築したいという需要は高まっています。本レポートでは、NVIDIA GTX 1660 SUPER（VRAM 6GB）という、現代のAIハードウェア基準から見れば「制約された」リソースを持つコンシューマー向けGPUを用いて、実用的なDeep Researchエージェントを構築するための包括的な技術戦略を提示します 4。

一般的な誤解として、高度な推論には数百億パラメータのモデル（70B+）と、それを格納するための数十ギガバイトのVRAM（A100やH100など）が不可欠であると考えられがちです 5。しかし、近年の「Small Language Models（SLM）」の性能向上、量子化技術の洗練、そしてLangGraphのようなグラフベースのオーケストレーションフレームワークの登場により、6GB VRAM環境であっても、アーキテクチャを工夫することで高度なタスク遂行が可能になっています 2。

本稿では、ハードウェアの物理的制約をソフトウェアの工夫で突破するための「外科的」なアーキテクチャを提案します。それは、巨大なモデルで力任せに処理するのではなく、特化型の小型モデルを組み合わせ、グラフ理論に基づいた厳密な状態管理と、コンテキスト（文脈）の徹底的な節約を行うアプローチです。GTX 1660 SUPERの限界を見極め、それを最大限に活用するためのモデル選定、推論エンジンのチューニング、そしてエージェントワークフローの設計に至るまで、徹底的な技術分析と実装ガイドラインを展開します。

## **2\. ハードウェア制約の詳細分析とVRAMエコノミクス**

Deep Researchエージェントの設計において、最初に行うべきはハードウェアリソースの厳密な計算です。GTX 1660 SUPERはTuringアーキテクチャを採用しており、6GBのGDDR6メモリを搭載しています。AIモデルの運用において、この6GBという容量は極めてシビアな境界線となります 4。

### **2.1 モデルウェイトとKVキャッシュのメモリ計算**

大規模言語モデル（LLM）をローカルで動作させる際、VRAMは主に「モデルの重み（Weights）」と「KVキャッシュ（Key-Value Cache）」、そして「計算用バッファ（Activation Overhead）」の3つの要素によって消費されます。

モデルの重みは、パラメータ数と量子化ビット数に依存します。通常、FP16（16ビット浮動小数点）精度では、10億パラメータあたり約2GBのVRAMが必要です。したがって、量子化されていない80億パラメータ（8B）のモデルは約16GBを必要とし、6GB VRAMには到底収まりません 5。しかし、GGUFフォーマットなどを用いた4ビット量子化（INT4）を適用することで、メモリ要件は劇的に低下します。INT4では10億パラメータあたり約0.7GB〜0.8GB程度まで圧縮可能です。これにより、7B〜8Bクラスのモデルが5.0GB〜6.0GB程度のサイズとなり、6GB VRAMへの搭載が視野に入ってきます 8。

しかし、ここで見落とされがちなのが「KVキャッシュ」の存在です。Deep Researchのようなタスクでは、大量のウェブ検索結果や文献をコンテキストとしてモデルに入力する必要があります。コンテキスト長（トークン数）が増加するにつれて、KVキャッシュのメモリ消費量は線形（あるいはアテンション機構によっては二次関数的）に増大します。8Bモデルにおいて、4ビット量子化（Q4\_K\_M）を適用しても、コンテキスト長を8192トークン（8k）まで拡張すると、KVキャッシュだけで1GB以上を消費する可能性があります 9。

| モデルクラス | パラメータ数 | 量子化手法 | 推定モデルサイズ | 推定KVキャッシュ (8k) | 合計VRAM要件 | GTX 1660 SUPERでの実行可能性 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Qwen 2.5** | 7B | Q4\_K\_M | \~4.6 GB | \~0.8 GB | **\~5.4 GB** | **高** (VRAM内に収まる可能性大) |
| **Llama 3.1** | 8B | Q4\_K\_M | \~4.9 GB | \~1.2 GB | **\~6.1 GB** | **中** (一部システムRAMへのオフロードが必要) |
| **DeepSeek R1** | 7B | Q4\_K\_M | \~4.6 GB | \~0.8 GB | **\~5.4 GB** | **高** (推論特化として最適) |
| **Mistral** | 7B (v0.3) | Q4\_K\_M | \~4.5 GB | \~0.9 GB | **\~5.4 GB** | **高** |
| **Llama 3.2** | 3B | Q8\_0 | \~3.4 GB | \~0.5 GB | **\~3.9 GB** | **極めて高** (高速処理用) |

表1：主要モデルのGTX 1660 SUPERにおけるメモリ要件の試算 7

上表の通り、7Bクラスのモデルであれば、Q4\_K\_M量子化を用いることで、ギリギリVRAM内に収めることができます。しかし、Llama 3.1 8Bのようにパラメータ数が若干多いモデルや、コンテキスト長を長く設定しすぎた場合、VRAM容量を超過します。

### **2.2 メモリ溢れとシステムRAMへのオフロード**

VRAM容量を超えた場合、多くの推論エンジン（OllamaやLlama.cpp）は、モデルの一部レイヤーをシステムRAM（メインメモリ）にオフロードする機能を持っています。しかし、GTX 1660 SUPERとCPU間の通信はPCIeバスを介して行われるため、VRAM内での処理に比べて速度が桁違いに低下します。VRAM内で完結していれば毎秒40〜50トークン（t/s）の生成が可能であっても、一部がシステムRAMに溢れた瞬間に、3〜5 t/s程度までパフォーマンスが劣化することが報告されています 9。

Deep Researchエージェントは、検索結果の読み込み、評価、要約といった処理を何十回、何百回と繰り返すため、推論速度の低下は致命的です。したがって、**「VRAM内に全ての処理を収める」**、あるいは\*\*「オフロードを最小限に抑える」\*\*ことが、システム設計上の最優先事項となります。これを実現するためには、単にモデルを小さくするだけでなく、コンテキスト管理の厳密化や、Flash Attentionなどの最適化技術の導入が不可欠です 9。

## **3\. 推論エンジンの選定と最適化：OllamaとLlama.cppの活用**

ハードウェアの制約を克服するためには、推論を実行するバックエンドエンジンの選択と設定が重要です。現在、ローカルLLM実行環境としては、vLLM、LM Studio、Ollama（Llama.cppベース）などが主流ですが、GTX 1660 SUPERのようなコンシューマーGPUにおいて最も効率的かつ安定して動作するのは、**Llama.cpp**をバックエンドに持つ**Ollama**です 11。

### **3.1 Ollamaのサーバー・クライアントアーキテクチャ**

Ollamaは、複雑なLlama.cppのコマンドライン操作を隠蔽し、REST APIを通じてモデルを利用可能にするサーバー・クライアント型のツールです。これにより、後述するLangGraphなどのPythonプログラムから容易にモデルを呼び出すことができます。

GTX 1660 SUPER環境でOllamaを使用する際、デフォルト設定のままでは性能を十分に引き出せない、あるいはメモリエラー（Out of Memory: OOM）が発生するリスクがあります。以下の環境変数設定によるチューニングが必須となります 9。

1. Flash Attentionの有効化 (OLLAMA\_FLASH\_ATTENTION=1):  
   Flash Attentionは、Transformerモデルのアテンション計算におけるメモリ使用量と計算時間を削減する技術です。これにより、同じVRAM容量でもより長いコンテキストを扱うことが可能になります。Deep Researchでは検索結果などの長文を読み込む機会が多いため、この設定は極めて重要です 9。  
2. KVキャッシュの量子化 (OLLAMA\_KV\_CACHE\_TYPE):  
   最新のLlama.cppおよびOllamaでは、KVキャッシュ自体のデータ型をFP16からQ8\_0（8ビット）やQ4\_0（4ビット）に量子化する機能がサポートされています。これにより、コンテキスト保持に必要なメモリ量を半分以下に削減できる場合があります。推論精度の低下は軽微であり、6GB VRAMで長い文脈を扱うための切り札となります 10。  
3. GPUレイヤー数の手動制御 (num\_gpu):  
   Ollamaは通常、可能な限り多くのレイヤーをGPUにロードしようとしますが、自動判定が最適でない場合があります。特に8Bモデルを使用する場合、システムRAMへの溢れ（Spill）を防ぐために、あえてGPUにロードするレイヤー数を制限（例えば全33レイヤー中25レイヤーなど）し、残りをCPU処理とすることで、速度と安定性のバランスをとる戦略も有効です。ただし、前述の通り速度低下は避けられないため、これは7B以下のモデルを使用できない場合の次善策となります 8。

### **3.2 コンテキストシフトとスライディングウィンドウ**

Deep Researchのような長時間稼働するエージェントでは、会話履歴や思考プロセスが蓄積され、コンテキスト長の上限に達することがあります。Llama.cppは、コンテキストが溢れた際に全トークンを再計算するのではなく、古いトークンを破棄して新しいトークンを追加する「コンテキストシフト」機能をサポートしています。これにより、長い調査プロセスにおいても、再計算による長い待ち時間を発生させずに継続的な推論が可能になります 13。

## **4\. モデル選定戦略：推論能力とリソースのバランス**

ハードウェアが固定されている以上、ソフトウェア（モデル）の選定がシステムの性能を決定づけます。2024年後半から2025年にかけて登場した高性能な小型モデル（SLM）は、6GB VRAM環境におけるDeep Researchの実現可能性を大きく引き上げました。

### **4.1 推論（Reasoning）モデルの台頭：DeepSeek R1 Distill**

従来の7Bクラスのモデルは、複雑な計画立案や論理的推論において、70Bクラスのモデルに大きく劣っていました。しかし、**DeepSeek R1**シリーズの登場により、この常識は覆されました。DeepSeek R1は、大規模モデルからの蒸留（Distillation）によって、小型モデルでありながら「思考の連鎖（Chain of Thought: CoT）」を行う能力を持っています 7。

具体的には、\<think\>タグを用いて内部的な思考プロセスを出力し、問題解決の手順を自己確認してから最終的な回答を生成します。この特性は、Deep Researchにおける「検索クエリの立案」や「情報の取捨選択」といった高度な判断業務に最適です。GTX 1660 SUPER向けには、**DeepSeek-R1-Distill-Qwen-7B**が最適な選択肢となります。Qwen 2.5 7Bをベースにしており、推論能力とメモリ効率のバランスが優れています 7。

### **4.2 作業（Worker）モデル：Qwen 2.5 と Llama 3.2**

推論モデルは強力ですが、思考プロセスを出力するため生成速度が遅く、トークン消費量も多くなります。単純なウェブページの要約やデータ抽出といったタスクには、より軽量で高速なモデルが適しています。  
Qwen 2.5 1.5BやLlama 3.2 3Bは、非常に軽量でありながら高い指示追従能力を持っています。これらのモデルは量子化すれば2GB〜3GB程度のVRAMで動作するため、推論モデルとメモリ上で共存させる、あるいは高速に切り替えて運用することが可能です 18。

### **4.3 ハイブリッドモデル戦略**

本レポートでは、単一のモデルですべてを行うのではなく、役割に応じたモデルの使い分け（ハイブリッド戦略）を推奨します。

* **Planner（計画者）:** DeepSeek-R1-Distill-Qwen-7B (Q4\_K\_M)  
  * 役割：ユーザーの問いを分解し、検索計画を立てる。最終レポートを執筆する。  
  * 特徴：論理的思考力が高いが、生成が遅い。  
* **Executor（実行者）:** Qwen 2.5 3B または 1.5B (Q4\_K\_M)  
  * 役割：検索された個別のウェブページを読み込み、要約を作成する。  
  * 特徴：極めて高速でメモリ消費が少ない。

この構成により、重い推論タスクは要所で行い、大量のテキスト処理は軽量モデルで行うことで、全体のスループットとメモリ効率を最大化します。

## **5\. エージェントフレームワークの設計：LangGraphの優位性**

複数のモデルとツール（検索エンジン、スクレイピング）を連携させ、自律的なワークフローを構築するためには、エージェントフレームワークが必要です。研究資料では、LangChain、AutoGen、CrewAI、LangGraphなどが挙げられていますが、Deep Researchの構築においては**LangGraph**が圧倒的に適しています 2。

### **5.1 なぜLangGraphなのか**

AutoGenやCrewAIは、エージェント同士の「会話」をベースにした高レベルな抽象化を提供します。これは実装が容易である反面、エージェント間の会話がループしたり、予期せぬ方向に脱線したりする制御不能な状態に陥りやすい欠点があります。また、会話履歴が膨大になりやすく、メモリ制約のある環境では致命的です 20。

対して**LangGraph**は、エージェントの挙動を\*\*「グラフ（ノードとエッジ）」\*\*として定義します。状態（State）を明示的に管理し、処理の流れ（Flow）を開発者が完全にコントロールできます。

* **循環（Cycles）のサポート:** 「検索→評価→不足があれば再検索」というDeep Research特有のループ処理を自然に記述できます。  
* **状態管理（State Management）:** エージェントが保持する情報を厳密に定義できます。例えば、「過去の全会話」を保持するのではなく、「現在までの要約済みレポート」のみを保持するように設計することで、コンテキスト消費を抑制できます。これは6GB VRAM環境では必須の機能です 2。

### **5.2 Deep Researchグラフのアーキテクチャ**

本システムでは、以下のようなノード構成を持つグラフを設計します。

1. Planner Node (計画ノード):  
   ユーザーの入力を受け取り、調査すべきサブトピック（Sub-questions）に分解します。DeepSeek R1を使用し、論理的な調査計画をJSON形式などで出力させます。  
2. Researcher Node (調査ノード):  
   計画に基づき、検索クエリを発行します。検索ツール（SearXNG）を呼び出し、URLリストを取得します。  
3. Scraper & Summarizer Node (取得・要約ノード):  
   取得したURLに対し、スクレイピングツール（Crawl4AI）を実行してコンテンツを取得します。ここで重要なのは、取得した生データをそのままコンテキストに入れるのではなく、即座に軽量モデル（Worker）で要約することです。これにより、数百ページの情報を扱ってもメモリが溢れることを防ぎます 25。  
4. Reviewer Node (評価ノード):  
   現在の情報で十分かどうかを判断します。不足していればResearcher Nodeに戻り（ループ）、十分であればWriter Nodeに進みます。  
5. Writer Node (執筆ノード):  
   蓄積された情報を統合し、最終的なレポートを作成します。

このアーキテクチャにより、エージェントはメモリ消費を抑えながら、無限に調査を継続することが可能になります。

## **6\. 検索とデータ取得：プライバシー重視のローカルスタック**

「ローカルで構築する」という趣旨に基づき、外部の有料API（TavilyやSerperなど）に依存せず、検索とスクレイピングもローカル環境で完結させる構成を採用します。

### **6.1 SearXNGによるメタ検索**

検索エンジンとして、オープンソースのメタ検索エンジンであるSearXNGをDockerコンテナで運用します。SearXNGは、Google、Bing、DuckDuckGoなど複数の検索エンジンの結果を集約し、広告やトラッキングを除去したクリーンな結果を返します 27。  
Deep Researchエージェントからは、SearXNGのAPIエンドポイントに対してクエリを投げ、JSON形式で検索結果（タイトル、URL、スニペット）を受け取ります。これにより、外部APIのレート制限やコストを気にすることなく、大量の検索を行うことが可能です。

### **6.2 Crawl4AIによるAIネイティブスクレイピング**

検索結果のURLから実際のコンテンツを取得するために、**Crawl4AI**を使用します。従来のスクレイピングツール（BeautifulSoupやSelenium）と比較して、Crawl4AIはLLM向けに最適化されている点が特徴です 29。

* **Markdown変換機能:** ウェブページの複雑なHTML構造（ヘッダー、フッター、サイドバー、広告など）を除去し、コンテンツの核心部分だけをクリーンなMarkdown形式に変換して抽出します。HTMLタグが含まれないため、LLMに入力する際のトークン数を大幅に節約できます。  
* **非同期処理:** 高速な非同期クロールが可能ですが、メモリ制約のあるローカルマシンでは、並列数を制限する必要があります。Crawl4AIは内部でヘッドレスブラウザ（Playwright）を使用するため、タブを開きすぎるとシステムRAMを圧迫します。本システムでは、一度に1ページずつ処理するシーケンシャルな設計が推奨されます 31。  
* **プルーニング（剪定）:** BM25などのアルゴリズムを用いて、クエリに関連性の低いテキストブロックを自動的に削除する機能もあります。これにより、さらにコンテキスト効率を高めることができます 33。

## **7\. 実装戦略とコード構成**

ここでは、実際にこのシステムを構築するための具体的な実装手順とコードの概念を解説します。

### **7.1 Docker Composeによる環境構築**

システム全体をDocker Composeで管理することで、依存関係を分離し、容易にデプロイできるようにします。docker-compose.yamlには、Ollama、SearXNG、そして必要に応じてOpen WebUI（チャットインターフェース）を定義します。

YAML

version: '3.8'

services:  
  ollama:  
    image: ollama/ollama:latest  
    container\_name: ollama  
    deploy:  
      resources:  
        reservations:  
          devices:  
            \- driver: nvidia  
              count: 1  
              capabilities: \[gpu\]  
    environment:  
      \- OLLAMA\_KEEP\_ALIVE=24h  
      \- OLLAMA\_FLASH\_ATTENTION=1  
    volumes:  
      \- ollama\_data:/root/.ollama  
    ports:  
      \- "11434:11434"

  searxng:  
    image: searxng/searxng:latest  
    container\_name: searxng  
    ports:  
      \- "8080:8080"  
    volumes:  
      \-./searxng:/etc/searxng  
    environment:  
      \- SEARXNG\_BASE\_URL=http://localhost:8080

volumes:  
  ollama\_data:

この構成により、http://localhost:11434でLLM推論が、http://localhost:8080で検索が可能になります。OLLAMA\_FLASH\_ATTENTION=1の設定を忘れないようにしてください 9。

### **7.2 Python環境とライブラリ**

エージェントのロジックはPythonで実装します。主要なライブラリは以下の通りです。

Bash

pip install langgraph langchain-ollama crawl4ai duckduckgo-search aiohttp

### **7.3 LangGraphによる状態定義とノード実装**

LangGraphにおける「状態（State）」の定義は、システムのメモリ管理そのものです。

Python

from typing import TypedDict, List, Annotated  
import operator

class ResearchState(TypedDict):  
    task: str                       \# ユーザーの元の質問  
    plan: List\[str\]                 \# 検索計画（サブクエリのリスト）  
    steps\_completed: int            \# 実行ステップ数  
    \# contentは過去の情報を上書きせず、追記していく（要約済み情報のみ）  
    content: Annotated\[List\[str\], operator.add\]   
    current\_search\_query: str       \# 現在実行中のクエリ  
    references: List\[str\]           \# 引用元のURLリスト

Plannerノードの実装イメージ:  
ここではDeepSeek R1モデルを呼び出しますが、JSON形式での出力を強制するプロンプトエンジニアリングが重要です。小型モデルはJSONモードの遵守が甘い場合があるため、出力結果をパースして失敗した場合は再生成するような堅牢性を持たせます 25。

Python

PLANNER\_PROMPT \= """  
あなたはプロの研究計画者です。以下のテーマについて調査するための3つの検索クエリを立案してください。  
出力は必ず以下のJSON形式のみにしてください。  
{{"queries": \["クエリ1", "クエリ2", "クエリ3"\]}}  
テーマ: {task}  
"""

Summarizerノードの実装イメージ:  
スクレイピングした生データ（Markdown）を要約する工程です。ここでは軽量なQwen 2.5 3Bなどを指定します。

Python

SUMMARIZE\_PROMPT \= """  
以下のテキストはウェブページの内容です。ユーザーの質問「{task}」に関連する重要な事実を抽出し、簡潔に要約してください。  
元のテキスト: {raw\_content}  
"""

このプロセスを経ることで、数万トークンの生データが数百トークンの要約に圧縮され、状態（State）に追加されます。これが6GB VRAMで長時間稼働を続けるための核心技術です。

## **8\. パフォーマンスチューニングと現実的な制約**

GTX 1660 SUPERでDeep Researchシステムを稼働させる場合、いくつかのトレードオフと限界を理解しておく必要があります。

### **8.1 速度とレイテンシ**

70Bモデルをクラウドで動かす場合とは異なり、ローカルの7BモデルでのDeep Researchは時間がかかります。1回の検索・読解サイクルに数分かかることも珍しくありません。特に、DeepSeek R1のような推論モデルは思考トークンを出力するため、生成に時間がかかります。  
ユーザー体験としては、チャットのような即答性を期待するのではなく、「タスクを投げて、数十分後にレポートを受け取る」バッチ処理的な運用が適しています。

### **8.2 ハルシネーション（幻覚）のリスク管理**

7Bクラスの小型モデルは、70Bクラスに比べて知識量が少なく、ハルシネーションを起こしやすい傾向があります。これを防ぐために、Reviewer Nodeにおいて「情報の整合性チェック」を行うステップを追加することが有効です。また、最終的なレポート生成時には、収集した情報の出典（URL）を明記させるようプロンプトで厳密に指示することで、情報の信頼性を担保します 36。

### **8.3 モデル切り替えのオーバーヘッド**

Planner用モデル（7B）とWorker用モデル（3B）を切り替える際、VRAMへのロード時間が発生します。NVMe SSDを使用している場合でも数秒のラグが生じます。頻繁な切り替えは全体の処理時間を延ばすため、可能な限り「計画フェーズ（一括）」→「調査フェーズ（一括）」→「執筆フェーズ」というように、同じモデルを使い続けるフェーズをまとめるバッチ処理的なグラフ設計が望ましいです。

## **9\. 結論と今後の展望**

GTX 1660 SUPER（6GB VRAM）という制約されたハードウェア環境においても、適切なアーキテクチャを採用することで、実用的なDeep Researchエージェントを構築することは十分に可能です。

その成功の鍵は以下の3点に集約されます。

1. **モデルの適材適所:** 推論能力の高いDeepSeek R1 Distillと、高速なQwen/Llamaの小型モデルをハイブリッドで運用すること。  
2. **徹底したコンテキスト管理:** Crawl4AIによるMarkdown化と、即時要約による情報の圧縮を行い、VRAM内のKVキャッシュを枯渇させないこと。  
3. **グラフベースの制御:** LangGraphを用いてステートフルな循環処理を実装し、エージェントの暴走を防ぎつつ自律性を確保すること。

このシステムは、クラウドAPIに依存しないため、プライバシーが完全に保たれ、ランニングコストも電気代のみです。今後、GGUF量子化技術のさらなる進化（例えば2ビット量子化の実用化）や、より高性能なSLMの登場により、このローカルDeep Research環境の性能はハードウェアを買い替えることなく向上していくでしょう。これは、巨大な計算資源を持つテック企業だけでなく、個人の開発者や研究者が自律型AIの恩恵を享受できる時代の到来を示唆しています。

### **推奨アクションプラン**

1. **Docker環境の整備:** NVIDIA Container Toolkitをインストールし、GPU対応Docker環境を構築する。  
2. **Ollamaの最適化:** OLLAMA\_FLASH\_ATTENTION=1を設定し、サーバーを起動する。  
3. **モデルのプル:** ollama pull deepseek-r1:7b および ollama pull qwen2.5:3b を実行する。  
4. **SearXNGのデプロイ:** Docker Composeを用いてローカル検索エンジンを立ち上げる。  
5. **LangGraphの実装:** PythonでPlanner、Researcher、Writerのノードを実装し、それらを接続する。まずはシンプルな「計画→検索→要約→執筆」の直線的なグラフから始め、徐々にループ処理を追加していくことを推奨します。

以上のアプローチにより、手元のGTX 1660 SUPERは、単なるグラフィックボードから、あなた専用の強力な知的パートナーへと変貌を遂げるはずです。

#### **引用文献**

1. Modern LLM Frameworks for Deep Research: Open-Source vs ..., 1月 15, 2026にアクセス、 [https://medium.com/@vi.ha.engr/modern-llm-frameworks-for-deep-research-open-source-vs-proprietary-solutions-642136c20078](https://medium.com/@vi.ha.engr/modern-llm-frameworks-for-deep-research-open-source-vs-proprietary-solutions-642136c20078)  
2. LangGraph 101: Let's Build A Deep Research Agent, 1月 15, 2026にアクセス、 [https://towardsdatascience.com/langgraph-101-lets-build-a-deep-research-agent/](https://towardsdatascience.com/langgraph-101-lets-build-a-deep-research-agent/)  
3. langchain-ai/open\_deep\_research \- GitHub, 1月 15, 2026にアクセス、 [https://github.com/langchain-ai/open\_deep\_research](https://github.com/langchain-ai/open_deep_research)  
4. Best agentic code LLM to run on laptop (6GB VRAM)? \- Reddit, 1月 15, 2026にアクセス、 [https://www.reddit.com/r/LocalLLaMA/comments/1pfnpcs/best\_agentic\_code\_llm\_to\_run\_on\_laptop\_6gb\_vram/](https://www.reddit.com/r/LocalLLaMA/comments/1pfnpcs/best_agentic_code_llm_to_run_on_laptop_6gb_vram/)  
5. Llama 3.1 \- 405B, 70B & 8B with multilinguality and long context, 1月 15, 2026にアクセス、 [https://huggingface.co/blog/llama31](https://huggingface.co/blog/llama31)  
6. Best Open-Source AI Agent Frameworks to Try in 2025, 1月 15, 2026にアクセス、 [https://www.alternates.ai/knowledge-hub/articles/best-open-source-ai-agent-frameworks-2025](https://www.alternates.ai/knowledge-hub/articles/best-open-source-ai-agent-frameworks-2025)  
7. Best Local LLMs for 8GB VRAM: Complete 2025 Performance Guide, 1月 15, 2026にアクセス、 [https://localllm.in/blog/best-local-llms-8gb-vram-2025](https://localllm.in/blog/best-local-llms-8gb-vram-2025)  
8. LM Studio VRAM Requirements for Local LLMs | LocalLLM.in, 1月 15, 2026にアクセス、 [https://localllm.in/blog/lm-studio-vram-requirements-for-local-llms](https://localllm.in/blog/lm-studio-vram-requirements-for-local-llms)  
9. Ollama VRAM Requirements: Complete 2025 Guide to GPU ..., 1月 15, 2026にアクセス、 [https://localllm.in/blog/ollama-vram-requirements-for-local-llms](https://localllm.in/blog/ollama-vram-requirements-for-local-llms)  
10. Context Kills VRAM: How to Run LLMs on consumer GPUs \- Medium, 1月 15, 2026にアクセス、 [https://medium.com/@lyx\_62906/context-kills-vram-how-to-run-llms-on-consumer-gpus-a785e8035632](https://medium.com/@lyx_62906/context-kills-vram-how-to-run-llms-on-consumer-gpus-a785e8035632)  
11. Choosing the right inference framework | LLM Inference Handbook, 1月 15, 2026にアクセス、 [https://bentoml.com/llm/getting-started/choosing-the-right-inference-framework](https://bentoml.com/llm/getting-started/choosing-the-right-inference-framework)  
12. How to Run a Local LLM: Complete Guide to Setup & Best Models ..., 1月 15, 2026にアクセス、 [https://blog.n8n.io/local-llm/](https://blog.n8n.io/local-llm/)  
13. Sliding Window Attention support merged into llama.cpp ... \- Reddit, 1月 15, 2026にアクセス、 [https://www.reddit.com/r/LocalLLaMA/comments/1kqye2t/sliding\_window\_attention\_support\_merged\_into/](https://www.reddit.com/r/LocalLLaMA/comments/1kqye2t/sliding_window_attention_support_merged_into/)  
14. SWA not working \- missing ContextShift toggle causes excessive ..., 1月 15, 2026にアクセス、 [https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1129](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1129)  
15. How to Increase Context Window Size in Docker Model Runner with ..., 1月 15, 2026にアクセス、 [https://www.ajeetraina.com/how-to-increase-context-window-size-in-docker-model-runner-with-llama-cpp/](https://www.ajeetraina.com/how-to-increase-context-window-size-in-docker-model-runner-with-llama-cpp/)  
16. Ask HN: What is the best LLM for consumer grade hardware?, 1月 15, 2026にアクセス、 [https://news.ycombinator.com/item?id=44134896](https://news.ycombinator.com/item?id=44134896)  
17. Run DeepSeek R1 locally on your device (Beginner-Friendly Guide), 1月 15, 2026にアクセス、 [https://www.jan.ai/post/deepseek-r1-locally](https://www.jan.ai/post/deepseek-r1-locally)  
18. 7 Fastest Open Source LLMs You Can Run Locally in 2025 \- Medium, 1月 15, 2026にアクセス、 [https://medium.com/@namansharma\_13002/7-fastest-open-source-llms-you-can-run-locally-in-2025-524be87c2064](https://medium.com/@namansharma_13002/7-fastest-open-source-llms-you-can-run-locally-in-2025-524be87c2064)  
19. Running with Ollama \- GPT Researcher, 1月 15, 2026にアクセス、 [https://docs.gptr.dev/docs/gpt-researcher/llms/running-with-ollama](https://docs.gptr.dev/docs/gpt-researcher/llms/running-with-ollama)  
20. AutoGen vs LangGraph: Comparing Multi-Agent AI Frameworks, 1月 15, 2026にアクセス、 [https://www.truefoundry.com/blog/autogen-vs-langgraph](https://www.truefoundry.com/blog/autogen-vs-langgraph)  
21. Build a custom RAG agent with LangGraph \- Docs by LangChain, 1月 15, 2026にアクセス、 [https://docs.langchain.com/oss/python/langgraph/agentic-rag](https://docs.langchain.com/oss/python/langgraph/agentic-rag)  
22. Top 7 Open Source AI Agent Frameworks for Building AI ... \- Adopt AI, 1月 15, 2026にアクセス、 [https://www.adopt.ai/blog/top-7-open-source-ai-agent-frameworks-for-building-ai-agents](https://www.adopt.ai/blog/top-7-open-source-ai-agent-frameworks-for-building-ai-agents)  
23. An Open-source Framework for Autonomous Language Agents, 1月 15, 2026にアクセス、 [https://www.reddit.com/r/LocalLLaMA/comments/16jl53m/agents\_an\_opensource\_framework\_for\_autonomous/](https://www.reddit.com/r/LocalLLaMA/comments/16jl53m/agents_an_opensource_framework_for_autonomous/)  
24. LangGraph vs AutoGen vs CrewAI: Complete AI Agent Framework ..., 1月 15, 2026にアクセス、 [https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langgraph-vs-autogen-vs-crewai-complete-ai-agent-framework-comparison-architecture-analysis-2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langgraph-vs-autogen-vs-crewai-complete-ai-agent-framework-comparison-architecture-analysis-2025)  
25. Building a Deep research agent with Qwen3 using LangGraph and ..., 1月 15, 2026にアクセス、 [https://dev.to/composiodev/a-comprehensive-guide-to-building-a-deep-research-agent-with-qwen3-locally-1jgm](https://dev.to/composiodev/a-comprehensive-guide-to-building-a-deep-research-agent-with-qwen3-locally-1jgm)  
26. Building Deep Agents with LangGraph: A Practical Guide \- Medium, 1月 15, 2026にアクセス、 [https://medium.com/@techofhp/building-deep-agents-with-langgraph-a-practical-guide-686422c1324e](https://medium.com/@techofhp/building-deep-agents-with-langgraph-a-practical-guide-686422c1324e)  
27. Open-webui install with Ollama and Seaxng for web searches, 1月 15, 2026にアクセス、 [https://www.youtube.com/watch?v=eZRNOdm4ub0](https://www.youtube.com/watch?v=eZRNOdm4ub0)  
28. How did I setup Ollama with SearXNG? | by Curious \- Medium, 1月 15, 2026にアクセス、 [https://medium.com/@always\_curi0us/how-did-i-setup-ollama-with-searxng-ea713f94f179](https://medium.com/@always_curi0us/how-did-i-setup-ollama-with-searxng-ea713f94f179)  
29. Self-Hosting Guide \- Crawl4AI Documentation (v0.7.x), 1月 15, 2026にアクセス、 [https://docs.crawl4ai.com/core/self-hosting/](https://docs.crawl4ai.com/core/self-hosting/)  
30. Crawl4AI vs Firecrawl: Detailed Comparison 2025 \- Scrapeless, 1月 15, 2026にアクセス、 [https://www.scrapeless.com/en/blog/crawl4ai-vs-firecrawl](https://www.scrapeless.com/en/blog/crawl4ai-vs-firecrawl)  
31. \[Bug\]: Memory Creep · Issue \#742 · unclecode/crawl4ai \- GitHub, 1月 15, 2026にアクセス、 [https://github.com/unclecode/crawl4ai/issues/742](https://github.com/unclecode/crawl4ai/issues/742)  
32. How to optimize the memory usage of my python crawler, 1月 15, 2026にアクセス、 [https://stackoverflow.com/questions/42661993/how-to-optimize-the-memory-usage-of-my-python-crawler](https://stackoverflow.com/questions/42661993/how-to-optimize-the-memory-usage-of-my-python-crawler)  
33. Crawl4AI breakdown \- Dwarves Memo, 1月 15, 2026にアクセス、 [https://memo.d.foundation/breakdown/crawl4ai](https://memo.d.foundation/breakdown/crawl4ai)  
34. Setting Up Ollama with Open-WebUI: A Docker Compose Guide, 1月 15, 2026にアクセス、 [https://www.archy.net/setting-up-ollama-with-open-webui-a-docker-compose-guide/](https://www.archy.net/setting-up-ollama-with-open-webui-a-docker-compose-guide/)  
35. Build Your First AI Agent in 2025 (Python \+ LangGraph): Step‑by ..., 1月 15, 2026にアクセス、 [https://skywork.ai/blog/build-ai-agent-python-langgraph-step-by-step-2025/](https://skywork.ai/blog/build-ai-agent-python-langgraph-step-by-step-2025/)  
36. Deep Research Agent in LangGraph with Semantic Memory via MCP, 1月 15, 2026にアクセス、 [https://medium.com/@gzozulin/deep-research-agent-in-langgraph-with-semantic-memory-via-mcp-f690c4f9fc24](https://medium.com/@gzozulin/deep-research-agent-in-langgraph-with-semantic-memory-via-mcp-f690c4f9fc24)