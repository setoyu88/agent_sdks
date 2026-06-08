# agents/

AIエージェント実装のコレクション。現在は Deep Agents（LangChain/LangGraph）による実装を収録している。

---

## ディレクトリ構成

```
agents/
└── deep_agents/
    ├── text_agent/              # AIテキスト処理エージェント（固定スキル版）
    │   ├── __init__.py
    │   ├── agent.py             # create_deep_agent ラッパー
    │   ├── cli.py               # Typer CLIエントリーポイント
    │   └── subagents.py         # 4つのサブエージェント定義
    └── multi_skill_agent/       # マルチスキルエージェント（動的スキル拡張版）
        ├── __init__.py
        ├── agent.py             # FilesystemBackendでSKILL.mdを動的ロードするエージェント生成
        ├── cli.py               # Typer CLIエントリーポイント
        └── skills/              # スキル定義ディレクトリ（SKILL.md形式）
            ├── summarize/
            │   └── SKILL.md
            ├── revise/
            │   └── SKILL.md
            ├── translate/
            │   └── SKILL.md
            └── spec-refine/
                └── SKILL.md
```

---

## deep_agents/text_agent — AIテキスト処理エージェント

Deep Agents（`create_deep_agent`）を使ってテキストの要約・推敲・翻訳・仕様書整備を行うCLIツール。

### アーキテクチャ

```
CLI (cli.py)
  └── build_agent()               ← オーケストレータ生成 (agent.py)
        └── create_deep_agent()   ← Deep Agents SDK
              └── subagents       ← 処理に応じた専用サブエージェント (subagents.py)
                    ├── summarize-agent   テキスト要約
                    ├── revise-agent      文章推敲
                    ├── translate-agent   日英翻訳
                    └── spec-refine-agent 仕様書ブラッシュアップ
```

オーケストレータが処理種別を判定し、対応するサブエージェントに委譲する。
会話履歴は LangGraph のメッセージ状態として保持され、`/quit` まで対話が続く。

### 前提条件

```powershell
# 環境変数の設定（.env ファイルまたはシェル）
$env:OPENAI_API_KEY = "sk-..."

# 依存パッケージのインストール
uv sync
```

### サブコマンド一覧

| コマンド | 説明 |
|----------|------|
| `summarize` | テキストを指定粒度・文数で要約する |
| `revise` | 読みやすさ・論理性・構造を改善し、改善提案を添える |
| `translate` | 日本語→英語 または 英語→日本語に翻訳する |
| `spec-refine` | 要件仕様書を構造化・曖昧語排除・過不足チェックする |

### 共通オプション

| オプション | 型 | デフォルト | 説明 |
|---|---|---|---|
| `--text TEXT` | str | — | 処理対象テキスト（直接入力）※1 |
| `--file PATH` | Path | — | 処理対象テキストファイルパス ※1 |
| `--model MODEL` | str | `openai:gpt-5-mini` | 使用LLMモデル |
| `--out PATH` | str | — | 結果保存先（ファイルまたはディレクトリ） |

※1 `--text` と `--file` はどちらか一方を必ず指定する。同時指定はエラー。

---

### 使い方

#### ヘルプ

```powershell
$env:PYTHONIOENCODING = "utf-8"

uv run python agents/deep_agents/text_agent/cli.py --help
uv run python agents/deep_agents/text_agent/cli.py summarize --help
uv run python agents/deep_agents/text_agent/cli.py translate --help
```

#### summarize — テキスト要約

```powershell
# ファイルを中程度の粒度（3〜5文）で要約
uv run python agents/deep_agents/text_agent/cli.py summarize --file input.txt

# テキストを直接入力して短く（1〜2文）要約
uv run python agents/deep_agents/text_agent/cli.py summarize --text "長い文章..." --length short

# 文数を指定（--sentences は --length より優先される）
uv run python agents/deep_agents/text_agent/cli.py summarize --file input.txt --sentences 3
```

`--length` の選択肢:

| 値 | 目安 |
|---|---|
| `short` | 1〜5文 |
| `medium`（デフォルト） | 5〜15文 |
| `long` | 15〜30文 |

#### revise — テキスト推敲

```powershell
uv run python agents/deep_agents/text_agent/cli.py revise --text "推敲したい文章..."
uv run python agents/deep_agents/text_agent/cli.py revise --file draft.txt
```

改善した文章と具体的な改善提案が返される。

#### translate — テキスト翻訳

```powershell
# 日本語 → 英語
uv run python agents/deep_agents/text_agent/cli.py translate --text "こんにちは" --to en

# 英語 → 日本語
uv run python agents/deep_agents/text_agent/cli.py translate --file document.txt --to ja
```

`--to` は `en`（英語）または `ja`（日本語）のみ指定可能。

#### spec-refine — 仕様書ブラッシュアップ

```powershell
uv run python agents/deep_agents/text_agent/cli.py spec-refine --file spec.md
uv run python agents/deep_agents/text_agent/cli.py spec-refine --text "機能要件: ..."
```

目的・機能要件・非機能要件・制約・ワークフローの構造化、曖昧語排除、過不足チェックを行う。
明確化が必要な箇所はエージェントがユーザへ質問する。

---

### 対話ループ

各コマンドは初回処理後に対話モードに入る。修正指示を入力すると再処理される。

```
処理中...

（AIの出力結果）

修正指示（/quit で終了 /save <path> で保存）: もっと簡潔にして
処理中...

（再生成された結果）

修正指示（/quit で終了 /save <path> で保存）: /save ./result.md
結果を保存しました: result.md

修正指示（/quit で終了 /save <path> で保存）: /quit
```

| 入力 | 動作 |
|---|---|
| 任意のテキスト | 修正指示として処理し、結果を再生成する |
| `/save <path>` | 最後のAI出力結果をファイルに保存する（ループは継続） |
| `/quit` | 対話ループを終了する |

AIサービス呼び出しに失敗した場合は最大3回自動リトライする。
AIが中間応答（「少々お待ちください」等）を返した場合は自動的に処理を継続し、完了後に表示する。

---

### 結果のファイル保存

#### 対話中に `/save` で保存（推奨）

対話ループ中に `/save <ファイルパス>` を入力すると、最後のAI出力をファイルに保存できる。保存後も対話は継続する。

```
修正指示（/quit で終了 /save <path> で保存）: /save ./result.md
結果を保存しました: result.md

修正指示（/quit で終了 /save <path> で保存）: /quit
```

#### 起動時オプション `--out` で保存

`/quit` 入力後に最後の結果を Markdown ファイルとして自動保存する。

```powershell
# ディレクトリ指定 → ファイル名を自動決定
uv run python agents/deep_agents/text_agent/cli.py summarize --file report.txt --out ./results
# → ./results/report_summarized.md に保存

uv run python agents/deep_agents/text_agent/cli.py revise --text "文章..." --out ./results
# → ./results/output.md に保存

# ファイルパスで直接指定
uv run python agents/deep_agents/text_agent/cli.py translate --file doc.txt --to en --out ./en_doc.md
```

ディレクトリ指定時のファイル名ルール:

| 入力方法 | サブコマンド | 生成ファイル名 |
|---|---|---|
| `--file input.txt` | `summarize` | `input_summarized.md` |
| `--file input.txt` | `revise` | `input_revised.md` |
| `--file input.txt` | `translate` | `input_translated.md` |
| `--file input.txt` | `spec-refine` | `input_spec_refined.md` |
| `--text "..."` | 任意 | `output.md` |

---

### カスタムモデル

`--model` オプションで使用LLMを切り替えられる。形式は `provider:model-name`。

```powershell
# GPT-4.1（より高精度）
uv run python agents/deep_agents/text_agent/cli.py summarize --file input.txt --model openai:gpt-4.1

# 別プロバイダ（deepagents が対応している場合）
uv run python agents/deep_agents/text_agent/cli.py revise --file draft.txt --model google_genai:gemini-2.0-flash
```

---

### テスト実行

```powershell
# このエージェント専用のテスト
uv run pytest tests/test_deep_agents_text_agent.py -v

# 全テスト
uv run pytest tests/ -v
```

---

### エラーメッセージ一覧

| エラー | メッセージ |
|---|---|
| `--text` と `--file` の同時指定 | `エラー: --text と --file は同時に指定できません` |
| 両方未指定 | `エラー: --text または --file を指定してください` |
| ファイルが存在しない | `エラー: ファイルが見つかりません: {path}` |
| 対応外の翻訳言語 | `エラー: 翻訳先言語は en または ja を指定してください` |
| AIリトライ中（n回目） | `警告: AI呼び出しに失敗しました（{n}回目）。リトライ中...` |
| 3回全失敗 | `エラー: AI呼び出しが3回失敗しました。セッションを終了します` |
| `--sentences` が0以下 | typer の引数バリデーションエラー |
| `--out` の親ディレクトリ不在 | `エラー: 保存先ディレクトリが存在しません: {path}` |

---

### 関連ファイル

| ファイル | 内容 |
|---|---|
| `specs/002-deepagents-text-agent/spec.md` | 機能仕様書 |
| `specs/002-deepagents-text-agent/plan.md` | 実装計画 |
| `specs/002-deepagents-text-agent/quickstart.md` | クイックスタートガイド |
| `tests/test_deep_agents_text_agent.py` | テストコード |

---

## deep_agents/multi_skill_agent — マルチスキルエージェント

`skills/` フォルダの TOML ファイルを動的に読み込み、後からスキルを追加・拡張できる汎用エージェント。

### アーキテクチャ

```
CLI (cli.py)
  └── build_agent()                 ← エージェント生成 (agent.py)
        └── create_deep_agent()     ← Deep Agents SDK (FilesystemBackend で SKILL.md を動的ロード)
              └── skills            ← skills/ フォルダから動的ロードされたスキル群
```

オーケストレータがユーザの指示を解釈し、最適なスキルに自動委譲する。

### 使い方

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:OPENAI_API_KEY = "sk-..."

# テキストを渡して処理指示を対話入力
uv run python agents/deep_agents/multi_skill_agent/cli.py --text "長い文章..."
uv run python agents/deep_agents/multi_skill_agent/cli.py --file document.txt
uv run python agents/deep_agents/multi_skill_agent/cli.py --file doc.txt --model openai:gpt-4.1
```

起動後に処理内容を自然言語で指示する:

```
指示（/quit で終了, /save <path> で保存）: 3文で要約して
（AI が summarize-agent を選択して要約を生成）

指示（/quit で終了, /save <path> で保存）: 英語に翻訳して
（AI が translate-agent を選択して翻訳を生成）

指示（/quit で終了, /save <path> で保存）: /save ./output.md
結果を保存しました: output.md

指示（/quit で終了, /save <path> で保存）: /quit
```

### スキルの追加方法

`agents/deep_agents/multi_skill_agent/skills/` フォルダに新しいサブディレクトリを作成し、その中に `SKILL.md` を置くと次回起動時から自動的に利用可能になる。

この仕様は [deepagents skills API](https://docs.langchain.com/oss/python/deepagents/skills) に準拠している。

#### ディレクトリ構造

```
skills/
└── my-skill/          ← スキル名と同名のディレクトリ（小文字英数字とハイフンのみ）
    └── SKILL.md       ← 必須: YAML frontmatter + markdown 手順
```

#### SKILL.md の形式

```markdown
---
name: my-skill
description: このスキルの機能説明。エージェントがスキル選択時に参照する（最大1024文字）。
---

# my-skill スキル

## 使用するタイミング

- ユーザが「○○して」「△△を」などを要求したとき

## 手順

1. ...
2. ...
```

| frontmatterフィールド | 必須 | 説明 |
|---|---|---|
| `name` | ✓ | スキル識別子（ディレクトリ名と完全一致が必要。小文字英数字とハイフンのみ） |
| `description` | ✓ | エージェントがスキル選択に使う説明文（最大1024文字） |

#### 追加例: コードレビュースキル

```powershell
New-Item -ItemType Directory "agents\deep_agents\multi_skill_agent\skills\code-review"
```

`agents/deep_agents/multi_skill_agent/skills/code-review/SKILL.md`:

```markdown
---
name: code-review
description: ソースコードのバグ・改善点・セキュリティ問題をレビューする。「レビューして」「コードを確認して」などの指示に使用する。
---

# code-review スキル

## 使用するタイミング

- ユーザが「レビューして」「コードを確認して」などを要求したとき

## 手順

1. 入力されたソースコードを分析する
2. 以下の観点でフィードバックをまとめる
   - バグ・潜在的エラー
   - パフォーマンス改善点
   - セキュリティ上の問題
   - コードの可読性・保守性
3. 日本語でフィードバックを出力する
```

次回起動時から `code-review` スキルが利用可能になる。

### テスト実行

```powershell
uv run pytest tests/test_deep_agents_multi_skill_agent.py -v
```
