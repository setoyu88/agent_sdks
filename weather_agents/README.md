# Agent SDK 機能比較: 天気予報エージェント

OpenAI Agents SDK と Deep Agents (LangChain) を使った天気予報エージェントの比較実装。  
都市名を入力すると、今日と明日の天気予報を返す。

---

## セットアップ

### 前提条件

- Python 3.13 以上
- [uv](https://docs.astral.sh/uv/) インストール済み
- OpenAI API キー

### インストール

プロジェクトルート（`agent_sdks/`）で実行する。

```powershell
uv sync
```

### 環境変数

プロジェクトルートに `.env` ファイルを作成し、OpenAI API キーを設定する。

```
OPENAI_API_KEY=sk-...
```

または PowerShell で直接設定する。

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

---

## 使用方法

プロジェクトルート（`agent_sdks/`）から実行する。

### OpenAI Agents SDK 版

```powershell
uv run python weather_agents/openai_sdk/weather_agent.py
```

### Deep Agents 版

```powershell
uv run python weather_agents/deep_agents/weather_agent.py
```

### 実行例

```
天気予報エージェント（OpenAI Agents SDK版）
都市名を入力してください（終了: 'quit'）
> 東京
東京の天気予報:

【今日 (2026-05-30)】
天気: 一部曇り
最高気温: 26.9℃ / 最低気温: 16.3℃

【明日 (2026-05-31)】
天気: 曇り
最高気温: 27.6℃ / 最低気温: 16.6℃

> quit
```

### 入力について

- 日本語・英語どちらの都市名も入力可能（「東京」「Tokyo」など）
- 終了するには `quit` を入力する

---

## テスト

プロジェクトルート（`agent_sdks/`）から実行する。

```powershell
# 全テスト実行
uv run pytest tests/ -v

# SDK 別に実行
uv run pytest tests/test_openai_sdk.py -v
uv run pytest tests/test_deep_agents.py -v

# 比較テストのみ
uv run pytest tests/test_comparison.py -v
```

---

## ディレクトリ構成

```
weather_agents/               ← このディレクトリ
├── shared/
│   └── weather_api.py        # Open-Meteo API クライアント（両実装共通）
├── openai_sdk/
│   └── weather_agent.py      # OpenAI Agents SDK 版エージェント
└── deep_agents/
    └── weather_agent.py      # Deep Agents 版エージェント
```

プロジェクト全体の構成は以下の通り。

```
agent_sdks/
├── weather_agents/           ← このパッケージ
├── tests/
│   ├── test_shared.py        # 共通モジュールテスト
│   ├── test_openai_sdk.py    # OpenAI Agents SDK 版テスト
│   ├── test_deep_agents.py   # Deep Agents 版テスト
│   └── test_comparison.py   # 両実装比較テスト
└── pyproject.toml
```

---

## 依存パッケージ

| パッケージ | 用途 |
|-----------|------|
| `openai-agents` | OpenAI Agents SDK |
| `deepagents` | Deep Agents (LangChain) |
| `langchain-openai` | Deep Agents から OpenAI モデルを使用するために必要 |
| `httpx` | Open-Meteo API 呼び出し |
| `python-dotenv` | `.env` ファイルから環境変数を読み込む |
