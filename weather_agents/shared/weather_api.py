"""Open-Meteo APIを使用した天気予報取得モジュール。"""

import httpx

# WMO気象コードの日本語マッピング
_WMO_CODE_MAP: dict[int, str] = {
    0: "快晴",
    1: "晴れ",
    2: "一部曇り",
    3: "曇り",
    45: "霧",
    48: "着氷霧",
    51: "霧雨（弱）",
    53: "霧雨",
    55: "霧雨（強）",
    61: "雨（弱）",
    63: "雨",
    65: "雨（強）",
    71: "雪（弱）",
    73: "雪",
    75: "雪（強）",
    77: "霰",
    80: "にわか雨（弱）",
    81: "にわか雨",
    82: "にわか雨（強）",
    85: "にわか雪（弱）",
    86: "にわか雪（強）",
    95: "雷雨",
    96: "雷雨（雹あり）",
    99: "雷雨（大雹あり）",
}

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _describe_weather(code: int) -> str:
    """WMO気象コードを日本語の天気説明に変換する。

    Args:
        code: WMO気象コード。

    Returns:
        日本語の天気説明文字列。
    """
    return _WMO_CODE_MAP.get(code, f"不明（コード: {code}）")


def get_weather_forecast(city: str) -> str:
    """都市名から今日と明日の天気予報を取得する。

    Open-Meteo APIを使用してAPIキーなしで天気情報を取得する。
    geocoding APIは英語（またはローマ字）の都市名のみを受け付けるため、
    日本語の都市名は呼び出し前に英語に変換すること。

    Args:
        city: 天気予報を取得したい都市名（英語またはローマ字表記）。

    Returns:
        今日と明日の天気予報を含むフォーマット済みテキスト。
        エラー時はエラーメッセージ文字列を返す。
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            geo_resp = client.get(
                _GEOCODING_URL,
                params={"name": city, "count": 1, "language": "ja"},
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"エラー: 「{city}」は見つかりませんでした。別の都市名を入力してください。"

        result = geo_data["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        timezone = result.get("timezone", "auto")
        display_name = result.get("name", city)

        with httpx.Client(timeout=10.0) as client:
            forecast_resp = client.get(
                _FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                    "timezone": timezone,
                    "forecast_days": 2,
                },
            )
            forecast_resp.raise_for_status()
            forecast_data = forecast_resp.json()

        daily = forecast_data["daily"]
        dates = daily["time"]
        codes = daily["weathercode"]
        temp_max = daily["temperature_2m_max"]
        temp_min = daily["temperature_2m_min"]

        lines = [f"{display_name}の天気予報:\n"]
        labels = ["今日", "明日"]
        for i, label in enumerate(labels):
            lines.append(f"【{label} ({dates[i]})】")
            lines.append(f"天気: {_describe_weather(codes[i])}")
            lines.append(f"最高気温: {temp_max[i]}℃ / 最低気温: {temp_min[i]}℃\n")

        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        return f"エラー: 天気情報の取得に失敗しました（HTTPエラー: {e.response.status_code}）。"
    except httpx.RequestError:
        return "エラー: 天気情報を取得できませんでした。ネットワーク接続を確認してください。"
    except (KeyError, IndexError):
        return "エラー: 天気データの解析に失敗しました。しばらく後で再試行してください。"
