"""Deep Agentsを使用した天気予報エージェント。

実行方法:
    uv run python weather_agents/deep_agents/weather_agent.py
"""

from deepagents import create_deep_agent
from weather_agents.shared.weather_api import get_weather_forecast


def get_weather(city: str) -> str:
    """都市の今日と明日の天気予報を取得する。英語またはローマ字の都市名を受け付ける。

    Args:
        city: 天気予報を取得したい都市名（英語またはローマ字表記）。

    Returns:
        今日と明日の天気予報を含むフォーマット済みテキスト。
    """
    return get_weather_forecast(city)


agent = create_deep_agent(
    model="openai:gpt-5-mini",
    tools=[get_weather],
    system_prompt=(
        "あなたは天気予報を回答するアシスタントです。日本語で回答してください。"
        "都市名が日本語で入力された場合は、英語のローマ字名に変換してから"
        "get_weatherツールを呼び出してください。"
        "例: 「東京」→ 'Tokyo'、「大阪」→ 'Osaka'、「京都」→ 'Kyoto'"
    ),
)


def _extract_text(content: str | list) -> str:
    """Deep Agentsのメッセージコンテンツからテキストを抽出する。

    Args:
        content: 文字列またはテキストブロックのリスト。

    Returns:
        プレーンテキスト文字列。
    """
    if isinstance(content, str):
        return content
    # リスト形式: [{'type': 'text', 'text': '...'}, ...]
    texts = [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"]
    return "\n".join(texts)


def main() -> None:
    """CLIの対話ループを実行する。"""
    print("天気予報エージェント（Deep Agents版）")
    print("都市名を入力してください（終了: 'quit'）")

    while True:
        city_input = input("> ").strip()
        if city_input.lower() in ("quit", "exit", "q"):
            break
        if not city_input:
            continue

        result = agent.invoke(
            {"messages": [{"role": "user", "content": f"{city_input}の天気を教えてください。"}]}
        )
        print(_extract_text(result["messages"][-1].content))
        print()


if __name__ == "__main__":
    main()
