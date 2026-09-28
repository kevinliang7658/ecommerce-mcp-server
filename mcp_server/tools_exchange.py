"""
工具一：汇率换算（mock 数据版）

跨境电商场景里，客服/运营 Agent 经常要回答"这个 $29.99 的东西折合人民币多少钱"。
大模型自己不知道今天的汇率（训练数据是旧的），所以要给它一个"查汇率"的工具。

mock 说明：真实项目把 RATES 换成银联/第三方汇率 API 的实时返回即可，
函数签名（入参出参）保持不变，MCP Server 那边一行不用改。
"""

# 基准货币为 USD 的 mock 汇率表（2025 年量级，仅演示，勿当真）
RATES = {
    "USD": 1.0,
    "CNY": 7.25,   # 1 美元 ≈ 7.25 人民币
    "EUR": 0.92,   # 1 美元 ≈ 0.92 欧元
    "JPY": 150.0,  # 1 美元 ≈ 150 日元
    "GBP": 0.79,   # 1 美元 ≈ 0.79 英镑
    "KRW": 1380.0, # 1 美元 ≈ 1380 韩元
}


def convert(amount: float, from_currency: str, to_currency: str) -> str:
    """
    汇率换算核心逻辑（纯函数，方便单测）。

    :param amount: 金额
    :param from_currency: 源币种，如 USD
    :param to_currency: 目标币种，如 CNY
    :return: 换算结果的中文描述字符串（直接给大模型念给用户听）
    """
    from_currency = from_currency.upper().strip()
    to_currency = to_currency.upper().strip()

    # 入参校验：工具被大模型调用时参数是模型生成的，必须防御（模型可能传错币种）
    if from_currency not in RATES:
        return f"暂不支持的币种：{from_currency}，支持：{', '.join(RATES.keys())}"
    if to_currency not in RATES:
        return f"暂不支持的币种：{to_currency}，支持：{', '.join(RATES.keys())}"
    if amount < 0:
        return "金额不能为负数。"

    # 换算路径：先折成美元，再折成目标币种
    usd_amount = amount / RATES[from_currency]
    result = usd_amount * RATES[to_currency]
    return f"{amount:.2f} {from_currency} ≈ {result:.2f} {to_currency}（参考汇率 1 USD = {RATES[to_currency]} {to_currency}，mock 演示数据）"
