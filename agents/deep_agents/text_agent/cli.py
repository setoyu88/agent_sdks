"""AIテキスト処理エージェント CLIエントリーポイント。"""
from __future__ import annotations

import enum
import sys
from pathlib import Path
from typing import Optional

# agents/ ディレクトリをsys.pathに追加してdeep_agentsを直接インポート可能にする
# （直接実行時・パッケージとして実行時の両方に対応）
_AGENTS_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _AGENTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_DIR)

import typer
from rich.console import Console

from deep_agents.text_agent.agent import build_agent
from deep_agents.text_agent.subagents import (
    get_revise_subagent,
    get_spec_refine_subagent,
    get_summarize_subagent,
    get_translate_subagent,
)

app = typer.Typer(help="AIテキスト処理エージェント (Deep Agents版)")
console = Console()

_SUBCOMMAND_SUFFIX = {
    "summarize": "_summarized",
    "revise": "_revised",
    "translate": "_translated",
    "spec-refine": "_spec_refined",
}

_MAX_RETRIES = 3

# 処理前の確認メッセージ（中間応答）を検出するパターン
_ACKNOWLEDGMENT_PATTERNS = (
    "少々お待ちください",
    "お待ちください",
    "処理します",
    "処理いたします",
    "要約します",
    "翻訳します",
    "改善します",
    "推敲します",
    "承知しました",
    "かしこまりました",
)
# 自動再呼び出しの最大回数（無限ループ防止）
_MAX_AUTO_CONTINUES = 3


class LengthEnum(str, enum.Enum):
    """要約粒度の選択肢。"""

    short = "short"
    medium = "medium"
    long = "long"


# ── バリデーション・入力読み込みヘルパー ──────────────────────────────────────


def validate_text_file_input(text: Optional[str], file: Optional[Path]) -> None:
    """--text と --file の排他バリデーション。

    Args:
        text: --text オプションの値
        file: --file オプションの値

    Raises:
        typer.BadParameter: --text と --file が両方指定または両方未指定の場合
    """
    if text is not None and file is not None:
        raise typer.BadParameter("エラー: --text と --file は同時に指定できません")
    if text is None and file is None:
        raise typer.BadParameter("エラー: --text または --file を指定してください")


def load_input_text(text: Optional[str], file_path: Optional[Path]) -> str:
    """入力テキストを取得する。

    Args:
        text: 直接入力テキスト
        file_path: 読み込むファイルパス

    Returns:
        入力テキスト文字列
    """
    if file_path is not None:
        if not file_path.exists():
            console.print(f"エラー: ファイルが見つかりません: {file_path}")
            raise typer.Exit(code=1)
        return file_path.read_text(encoding="utf-8")
    return text  # type: ignore[return-value]


# ── ファイル保存ヘルパー ────────────────────────────────────────────────────


def resolve_output_path(
    out_path: str, input_file: Optional[Path], subcommand: str
) -> Path:
    """保存先ファイルパスを解決する。

    Args:
        out_path: --out オプションの値
        input_file: --file オプションで指定されたファイルパス
        subcommand: 実行したサブコマンド名

    Returns:
        保存先ファイルパス

    Raises:
        typer.Exit: 親ディレクトリが存在しない場合
    """
    p = Path(out_path)
    if p.suffix:
        if not p.parent.exists():
            console.print(f"エラー: 保存先ディレクトリが存在しません: {p.parent}")
            raise typer.Exit(code=1)
        return p

    if not p.exists():
        console.print(f"エラー: 保存先ディレクトリが存在しません: {p}")
        raise typer.Exit(code=1)

    suffix = _SUBCOMMAND_SUFFIX.get(subcommand, "")
    if input_file is not None:
        filename = f"{input_file.stem}{suffix}.md"
    else:
        filename = "output.md"
    return p / filename


def save_result_to_markdown(content: str, file_path: Path) -> None:
    """処理結果をMarkdownファイルに保存する。

    Args:
        content: 保存するテキスト内容
        file_path: 保存先ファイルパス
    """
    file_path.write_text(content, encoding="utf-8")


# ── 対話ループ ──────────────────────────────────────────────────────────────


def _get_last_ai_content(result: dict) -> str:
    """エージェント呼び出し結果から最後のAIメッセージ内容を取得する。"""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        role = getattr(msg, "type", None) or (
            msg.get("role") if isinstance(msg, dict) else None
        )
        if role in ("ai", "assistant"):
            content = getattr(msg, "content", None) or (
                msg.get("content") if isinstance(msg, dict) else ""
            )
            if isinstance(content, list):
                texts = [
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                ]
                return "".join(texts)
            return str(content) if content else ""
    return ""


def _invoke_with_retry(agent, messages: list) -> Optional[dict]:
    """エージェントをリトライ付きで呼び出す。

    Args:
        agent: 呼び出すエージェント
        messages: メッセージ履歴

    Returns:
        呼び出し結果。3回失敗した場合は None
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with console.status("処理中..."):
                result = agent.invoke({"messages": messages})
            return result
        except Exception:
            if attempt < _MAX_RETRIES:
                console.print(
                    f"警告: AI呼び出しに失敗しました（{attempt}回目）。リトライ中..."
                )
            else:
                console.print(
                    "エラー: AI呼び出しが3回失敗しました。セッションを終了します"
                )
    return None


def _is_acknowledgment_only(content: str) -> bool:
    """処理前の確認メッセージのみかを判定する。

    Args:
        content: AIの応答テキスト

    Returns:
        中間確認メッセージのみの場合True
    """
    if len(content.strip()) > 200:
        return False
    return any(pattern in content for pattern in _ACKNOWLEDGMENT_PATTERNS)


def _invoke_to_completion(agent, messages: list) -> Optional[dict]:
    """処理完了まで自動継続しながらエージェントを呼び出す。

    AIが「少々お待ちください」等の中間応答を返した場合、自動的に再呼び出しする。

    Args:
        agent: 呼び出すエージェント
        messages: メッセージ履歴

    Returns:
        呼び出し結果。失敗した場合は None
    """
    last_result = None
    current_messages = messages
    for _ in range(_MAX_AUTO_CONTINUES):
        result = _invoke_with_retry(agent, current_messages)
        if result is None:
            return None
        last_result = result
        content = _get_last_ai_content(result)
        if not _is_acknowledgment_only(content):
            return result
        current_messages = result.get("messages", current_messages)
    return last_result


def _handle_save_command(content: str, path_str: str) -> None:
    """保存コマンドを処理する。

    Args:
        content: 保存するテキスト内容
        path_str: 保存先ファイルパス文字列
    """
    save_path = Path(path_str)
    if not save_path.parent.exists():
        console.print(f"エラー: 保存先ディレクトリが存在しません: {save_path.parent}")
        return
    save_result_to_markdown(content, save_path)
    console.print(f"結果を保存しました: {save_path}")


def run_interactive_loop(
    agent,
    initial_messages: list[dict],
    subcommand: str,
    out_path: Optional[str],
    input_file: Optional[Path] = None,
) -> None:
    """対話ループを実行する。

    Args:
        agent: 使用するエージェント
        initial_messages: 初回メッセージリスト
        subcommand: 実行しているサブコマンド名
        out_path: 結果保存先パス（Noneなら保存しない）
        input_file: --file オプションで指定されたファイルパス
    """
    messages = list(initial_messages)
    last_ai_content = ""
    need_invoke = True

    while True:
        if need_invoke:
            result = _invoke_to_completion(agent, messages)
            if result is None:
                return
            messages = result.get("messages", messages)
            last_ai_content = _get_last_ai_content(result)
            console.print(last_ai_content)

        try:
            user_input = input("修正指示（/quit で終了, /save <path> で保存）: ")
        except EOFError:
            break

        stripped = user_input.strip()

        if stripped == "/quit":
            break

        if stripped.lower() == "/save" or stripped.lower().startswith("/save "):
            path_str = stripped[5:].strip()  # "/save" の後ろを取り出す
            if not path_str:
                console.print("エラー: 保存先パスを指定してください")
            elif last_ai_content:
                _handle_save_command(last_ai_content, path_str)
            else:
                console.print("エラー: 保存する内容がありません")
            need_invoke = False
        else:
            messages = list(messages) + [{"role": "user", "content": user_input}]
            need_invoke = True

    if out_path is not None and last_ai_content:
        save_path = resolve_output_path(out_path, input_file, subcommand)
        save_result_to_markdown(last_ai_content, save_path)
        console.print(f"結果を保存しました: {save_path}")


# ── サブコマンド ────────────────────────────────────────────────────────────


@app.command()
def summarize(
    text: Optional[str] = typer.Option(None, "--text", help="処理対象テキスト（直接入力）"),
    file: Optional[Path] = typer.Option(None, "--file", help="処理対象テキストファイルパス"),
    length: LengthEnum = typer.Option(LengthEnum.medium, "--length", help="要約の粒度 (short/medium/long)"),
    sentences: Optional[int] = typer.Option(None, "--sentences", help="要約文数（指定時は --length より優先）", min=1),
    model: str = typer.Option("openai:gpt-5-mini", "--model", help="使用LLMモデル"),
    out: Optional[str] = typer.Option(None, "--out", help="結果保存先ファイル/ディレクトリパス"),
) -> None:
    """テキストを指定粒度・文数で要約する。"""
    validate_text_file_input(text, file)
    input_text = load_input_text(text, file)

    if sentences is not None:
        length_instruction = f"{sentences}文で要約してください。"
    elif length == LengthEnum.short:
        length_instruction = "1〜5文で要約してください。"
    elif length == LengthEnum.long:
        length_instruction = "15〜30文で要約してください。"
    else:
        length_instruction = "5〜15文で要約してください。"

    initial_prompt = f"以下のテキストを{length_instruction}\n\n{input_text}"
    agent = build_agent(model=model, subagents=[get_summarize_subagent()])
    run_interactive_loop(
        agent=agent,
        initial_messages=[{"role": "user", "content": initial_prompt}],
        subcommand="summarize",
        out_path=out,
        input_file=file,
    )


@app.command()
def revise(
    text: Optional[str] = typer.Option(None, "--text", help="処理対象テキスト（直接入力）"),
    file: Optional[Path] = typer.Option(None, "--file", help="処理対象テキストファイルパス"),
    model: str = typer.Option("openai:gpt-5-mini", "--model", help="使用LLMモデル"),
    out: Optional[str] = typer.Option(None, "--out", help="結果保存先ファイル/ディレクトリパス"),
) -> None:
    """テキストの読みやすさ・論理性・構造を改善する。"""
    validate_text_file_input(text, file)
    input_text = load_input_text(text, file)

    initial_prompt = f"以下の文章を推敲し、改善した文章と具体的な改善提案を提示してください。\n\n{input_text}"
    agent = build_agent(model=model, subagents=[get_revise_subagent()])
    run_interactive_loop(
        agent=agent,
        initial_messages=[{"role": "user", "content": initial_prompt}],
        subcommand="revise",
        out_path=out,
        input_file=file,
    )


@app.command()
def translate(
    text: Optional[str] = typer.Option(None, "--text", help="処理対象テキスト（直接入力）"),
    file: Optional[Path] = typer.Option(None, "--file", help="処理対象テキストファイルパス"),
    to: str = typer.Option(..., "--to", help="翻訳先言語 (en または ja)"),
    model: str = typer.Option("openai:gpt-5-mini", "--model", help="使用LLMモデル"),
    out: Optional[str] = typer.Option(None, "--out", help="結果保存先ファイル/ディレクトリパス"),
) -> None:
    """テキストを日本語/英語に翻訳する。"""
    if to not in ("en", "ja"):
        console.print("エラー: 翻訳先言語は en または ja を指定してください")
        raise typer.Exit(code=1)

    validate_text_file_input(text, file)
    input_text = load_input_text(text, file)

    lang_name = "英語" if to == "en" else "日本語"
    initial_prompt = f"以下のテキストを{lang_name}({to})に翻訳してください。\n\n{input_text}"
    agent = build_agent(model=model, subagents=[get_translate_subagent()])
    run_interactive_loop(
        agent=agent,
        initial_messages=[{"role": "user", "content": initial_prompt}],
        subcommand="translate",
        out_path=out,
        input_file=file,
    )


@app.command(name="spec-refine")
def spec_refine(
    text: Optional[str] = typer.Option(None, "--text", help="処理対象テキスト（直接入力）"),
    file: Optional[Path] = typer.Option(None, "--file", help="処理対象テキストファイルパス"),
    model: str = typer.Option("openai:gpt-5-mini", "--model", help="使用LLMモデル"),
    out: Optional[str] = typer.Option(None, "--out", help="結果保存先ファイル/ディレクトリパス"),
) -> None:
    """要件仕様書を構造化・改善する。"""
    validate_text_file_input(text, file)
    input_text = load_input_text(text, file)

    initial_prompt = (
        "以下の要件仕様書を構造化・改善してください。"
        "目的・機能要件・非機能要件・制約・ワークフローに整理し、"
        "曖昧語を排除し、過不足をチェックしてください。"
        "明確化に必要な点があればユーザへ質問してください。\n\n"
        f"{input_text}"
    )
    agent = build_agent(model=model, subagents=[get_spec_refine_subagent()])
    run_interactive_loop(
        agent=agent,
        initial_messages=[{"role": "user", "content": initial_prompt}],
        subcommand="spec-refine",
        out_path=out,
        input_file=file,
    )


if __name__ == "__main__":
    app()
