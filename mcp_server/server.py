"""
电商工具箱 MCP Server（入口）

MCP（Model Context Protocol）一句话：
  一个开放协议，让大模型客户端（Claude Desktop、Kimi Code 等）能安全地调用
  你本地/公司内网的"工具"。你只需要用装饰器把普通 Python 函数登记成工具，
  模型端就能自动发现它、在需要时调用它。

@mcp.tool() 把普通函数"暴露"给模型端；
  函数的 docstring 是模型判断"该不该调、怎么传参"的唯一依据，
  所以每个工具的 docstring 必须写清楚。

运行方式：
  直接 python server.py 会以 stdio 模式启动（等 MCP 客户端来连接，平时不用手动跑）。
  真正的用法是在 Claude Desktop / Kimi Code 里配置它（见 docs/01 文档）。
  想快速自测工具逻辑：python server.py --self-test
"""

import sys

from mcp.server.fastmcp import FastMCP

import tools_copywriting
import tools_exchange
import tools_logistics

# 创建 MCP Server 实例，名字会显示在客户端的工具列表里
mcp = FastMCP("电商工具箱")


@mcp.tool()
def exchange_rate_convert(amount: float, from_currency: str, to_currency: str) -> str:
    """汇率换算。当用户询问不同币种之间的金额换算时使用（例如"29.99美元多少人民币"）。

    :param amount: 要换算的金额
    :param from_currency: 源币种三位代码（USD/CNY/EUR/JPY/GBP/KRW）
    :param to_currency: 目标币种三位代码（USD/CNY/EUR/JPY/GBP/KRW）
    """
    return tools_exchange.convert(amount, from_currency, to_currency)


@mcp.tool()
def logistics_track(tracking_no: str) -> str:
    """查询跨境包裹的物流轨迹。当用户提供物流单号、询问包裹位置或签收状态时使用。

    :param tracking_no: 物流单号（演示单号：YT10001、YT10002）
    """
    return tools_logistics.query(tracking_no)


@mcp.tool()
def marketing_copy_generate(product_name: str, selling_points: str, platform: str = "亚马逊") -> str:
    """生成跨境电商营销文案（英文标题+5条卖点描述）。当用户要求为商品写推广/上架文案时使用。

    :param product_name: 商品名称
    :param selling_points: 卖点列表，用逗号分隔，如"降噪,续航30小时"
    :param platform: 投放平台，如 亚马逊/速卖通/独立站，默认亚马逊
    """
    return tools_copywriting.generate(product_name, selling_points, platform)


def self_test() -> None:
    """不依赖任何 MCP 客户端的本地自测：直接调三个工具看输出。"""
    print("--- 工具1：汇率换算 ---")
    print(exchange_rate_convert(29.99, "USD", "CNY"))
    print("\n--- 工具2：物流轨迹 ---")
    print(logistics_track("YT10001"))
    print("\n--- 工具3：营销文案（未配 key 时为模板输出） ---")
    print(marketing_copy_generate("无线蓝牙耳机", "主动降噪,续航30小时,蓝牙5.3", "速卖通"))


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        # stdio 模式：作为 MCP 客户端的子进程运行，通过标准输入输出收发协议消息
        # 手动运行时看起来会"卡住"，那是在等客户端连接，属正常现象
        mcp.run()
