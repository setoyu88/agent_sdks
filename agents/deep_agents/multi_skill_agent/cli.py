"""マルチスキルエージェント CLIエントリーポイント。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# agents/ ディレクトリをsys.pathに追加してdeep_agentsを直接インポート可能にする
_AGENTS_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _AGENTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_DIR)

import typer
from rich.console import Console

from deep_agents.multi_skill_agent.agent import build_agent

app = typer.Typer(help="マルチスキルAIエージェント（Deep Agents版）")
console = Console()

_MAX_RETRIES = 3
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
_MAX_AUTO_CONTINUES = 3


# ── 入力読み込みヘルパー ────────────────────────────────────────────────────────


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


# ── AIメッセージ処理ヘルパー ────────────────────────────────────────────────────


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


def _invoke_to_completion(agent, messages: list) -> Optional[dict]:
    """処理完了まで自動継続しながらエージェントを呼び出す。

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
    save_path.write_text(content, encoding="utf-8")
    console.print(f"結果を保存しました: {save_path}")


# ── 対話ループ ──────────────────────────────────────────────────────────────────


def run_interactive_loop(agent, initial_messages: list[dict]) -> None:
    """対話ループを実行する。

    Args:
        agent: 使用するエージェント
        initial_messages: 初回メッセージリスト
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
            user_input = input("指示（/quit で終了, /save <path> で保存）: ")
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


# ── コマンド ───────────────────────────────────────────────────────────────────


@app.command()
def run(
    text: Optional[str] = typer.Option(None, "--text", help="処理対象テキスト（直接入力）"),
    file: Optional[Path] = typer.Option(None, "--file", help="処理対象テキストファイルパス"),
    model: str = typer.Option("openai:gpt-5-mini", "--model", help="使用LLMモデル"),
) -> None:
    """マルチスキルエージェントでテキストを処理する。

    処理内容はユーザが自然言語で指示すると、エージェントが最適なスキルを選択して実行する。
    """
    validate_text_file_input(text, file)
    input_text = load_input_text(text, file)

    agent = build_agent(model=model)
    run_interactive_loop(
        agent=agent,
        initial_messages=[
            {
                "role": "user",
                "content": (
                    "以下のテキストを処理する準備ができました。"
                    "処理内容を指示してください（例: 要約して、英語に翻訳して、推敲して）。\n\n"
                    f"{input_text}"
                ),
            }
        ],
    )


if __name__ == "__main__":
    app()
