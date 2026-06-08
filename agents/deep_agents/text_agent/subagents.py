"""Deep Agentsサブエージェント定義モジュール。"""


def get_summarize_subagent() -> dict:
    """要約サブエージェントの定義を返す。

    Returns:
        要約サブエージェントの設定辞書
    """
    return {
        "name": "summarize-agent",
        "description": "入力テキストを指定粒度・文数で要約する",
        "system_prompt": (
            "入力テキストを日本語で要約してください。"
            "--sentences N が指定された場合はN文を目安に要約してください。"
            "--length が指定された場合は N文字数を目安として要約してください。"
            "要約のみを出力し、余分な説明は付け加えないでください。"
        ),
    }


def get_revise_subagent() -> dict:
    """推敲サブエージェントの定義を返す。

    Returns:
        推敲サブエージェントの設定辞書
    """
    return {
        "name": "revise-agent",
        "description": "文章の読みやすさ・論理性・構造を改善し改善提案を提示する",
        "system_prompt": (
            "入力文章の文体・論理構造・読みやすさを改善し、"
            "改善した文章と具体的な改善提案を日本語で提示してください。"
            "改善文章と改善提案を明確に区別して出力してください。"
        ),
    }


def get_translate_subagent() -> dict:
    """翻訳サブエージェントの定義を返す。

    Returns:
        翻訳サブエージェントの設定辞書
    """
    return {
        "name": "translate-agent",
        "description": "日本語/英語の翻訳を行う",
        "system_prompt": (
            "入力テキストを指定言語 (en: 英語、ja: 日本語) に正確に翻訳してください。"
            "対応言語は日本語と英語のみです。"
            "翻訳結果のみを出力し、余分な説明は付け加えないでください。"
        ),
    }


def get_spec_refine_subagent() -> dict:
    """仕様書ブラッシュアップサブエージェントの定義を返す。

    Returns:
        仕様書ブラッシュアップサブエージェントの設定辞書
    """
    return {
        "name": "spec-refine-agent",
        "description": "要件仕様書の構造化・曖昧語排除・過不足チェックを行い必要に応じてユーザへ質問する",
        "system_prompt": (
            "入力された要件仕様書の構造化（目的・機能要件・非機能要件・制約・ワークフロー）・"
            "曖昧語排除・過不足チェックを行い、改善仕様書を日本語で提示してください。"
            "明確化が必要な箇所はユーザへ質問してください。"
        ),
    }
