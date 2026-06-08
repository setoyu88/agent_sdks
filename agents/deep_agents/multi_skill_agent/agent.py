"""マルチスキルエージェントオーケストレータ生成モジュール。"""
from __future__ import annotations

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

_MULTI_SKILL_DIR = Path(__file__).parent
# スキルディレクトリへの相対パス（POSIX形式、FilesystemBackend の root_dir 基準）
_SKILLS_SOURCE = "skills/"


def build_agent(model: str):
    """skills/ フォルダの SKILL.md を動的に読み込んでエージェントを生成する。

    skills/<skill-name>/SKILL.md の YAML frontmatter(name・description)と
    markdown 本文（手順・指示）を deepagents の skills API で読み込む。

    Args:
        model: 使用するLLMモデル(例: "openai:gpt-5-mini")

    Returns:
        設定済みのDeep Agentインスタンス
    """
    backend = FilesystemBackend(root_dir=str(_MULTI_SKILL_DIR), virtual_mode=False)
    return create_deep_agent(
        model=model,
        backend=backend,
        skills=[_SKILLS_SOURCE],
        system_prompt=(
            "あなたはマルチスキルのオーケストレータです。"
            "ユーザの指示を受け取ったら、最適なスキルを選択し実行してください。"
            "「少々お待ちください」「処理します」等の中間メッセージは出力しないでください。"
            "常にスキルの処理結果をそのまま返してください。"
            "日本語で回答してください。"
        ),
    )
