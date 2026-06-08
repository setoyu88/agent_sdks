"""OpenAI Agents SDKを使用した天気予報エージェント。

実行方法:
    uv run python weather_agents/openai_sdk/weather_agent.py
"""

from agents import Agent, Runner, function_tool
from weather_agents.shared.weather_api import get_weather_forecast


@function_tool
def get_weather(city: str) -> str:
    """都市の今日と明日の天気予報を取得する。英語またはローマ字の都市名を受け付ける。

    Args:
        city: 天気予報を取得したい都市名（英語またはローマ字表記）。

    Returns:
        今日と明日の天気予報を含むフォーマット済みテキスト。
    """
    return get_weather_forecast(city)


agent = Agent(
    name="天気予報エージェント（OpenAI Agents SDK版）",
    instructions=(
        "あなたは天気予報を回答するアシスタントです。日本語で回答してください。"
        "都市名が日本語で入力された場合は、英語のローマ字名に変換してから"
        "get_weatherツールを呼び出してください。"
        "例: 「東京」→ 'Tokyo'、「大阪」→ 'Osaka'、「京都」→ 'Kyoto'"
    ),
    model="gpt-5-mini",
    tools=[get_weather],
)


def main() -> None:
    """CLIの対話ループを実行する。"""
    print("天気予報エージェント（OpenAI Agents SDK版）")
    print("都市名を入力してください（終了: 'quit'）")

    while True:
        city_input = input("> ").strip()
        if city_input.lower() in ("quit", "exit", "q"):
            break
        if not city_input:
            continue

        result = Runner.run_sync(agent, f"{city_input}の天気を教えてください。")
        print(result.final_output)
        print()


if __name__ == "__main__":
    main()
