"""Deep Agentsオーケストレータ生成モジュール。"""
from deepagents import create_deep_agent


def build_agent(model: str, subagents: list[dict]):
    """エージェントを生成して返す。

    Args:
        model: 使用するLLMモデル（例: "openai:gpt-5-mini"）
        subagents: サブエージェント定義のリスト

    Returns:
        設定済みのDeep Agentインスタンス
    """
    return create_deep_agent(
        model=model,
        system_prompt=(
            "あなたはテキスト処理のオーケストレータです。"
            "ユーザの指示を受け取ったら、即座に対応するサブエージェントに処理を委譲し、結果を返してください。"
            "「少々お待ちください」「処理します」等の中間メッセージは出力しないこと。"
            "常にサブエージェントの処理結果をそのまま返してください。"
            "日本語で回答してください。"
        ),
        subagents=subagents,
    )
