"""
工具三：营销文案生成（真实调用 DeepSeek）

前两个工具是"查数据"，这个工具是"生成内容"：
把商品信息按成熟 Prompt 模板包好，调 DeepSeek 生成电商营销文案。

为什么要包成工具而不是让大模型直接写？
  1) Prompt 模板沉淀在服务端，业务方不用人人会写 Prompt；
  2) 温度、输出结构等参数统一管控，产出质量稳定；
  3) 以后换模型（DeepSeek -> 私有化 qwen2.5）只改这一个文件。

可以看成一个"文案微服务"，只是调用方从业务代码变成了大模型。
"""

import os

# base_url 对照表（换厂商时改这里）：
#   DeepSeek   https://api.deepseek.com                              model: deepseek-chat
#   通义千问   https://dashscope.aliyuncs.com/compatible-mode/v1     model: qwen-plus
#   智谱GLM    https://open.bigmodel.cn/api/paas/v4                  model: glm-4-flash
#   Kimi       https://api.moonshot.cn/v1                            model: moonshot-v1-8k
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 没配时走下方模板文案兜底
DEEPSEEK_MODEL = "deepseek-flash"


def generate(product_name: str, selling_points: str, platform: str = "亚马逊") -> str:
    """
    生成电商营销文案。

    :param product_name: 商品名，如"无线蓝牙耳机"
    :param selling_points: 卖点，多个用逗号分隔，如"降噪,续航30小时,蓝牙5.3"
    :param platform: 投放平台，如 亚马逊/速卖通/独立站
    :return: 生成的文案（标题 + 五点描述风格）
    """
    # 没配 key 时返回模板文案，保证整个 MCP Server 离线也能演示
    if not DEEPSEEK_API_KEY:
        points = [p.strip() for p in selling_points.split(",") if p.strip()]
        bullets = "\n".join(f"  - {p}" for p in points)
        return (
            f"【模板文案（未配置 DEEPSEEK_API_KEY，未调用大模型）】\n"
            f"{platform} | {product_name}\n"
            f"核心卖点：\n{bullets}\n"
            f"配置 DEEPSEEK_API_KEY 后，这里将由大模型生成地道营销文案。"
        )

    from openai import OpenAI  # 延迟导入，无 key 场景不加载

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    prompt = f"""你是一名跨境电商资深文案。请为以下商品写一段投放 {platform} 的营销文案：
                商品：{product_name}
                卖点：{selling_points}

                要求：
                1. 输出英文标题（含核心关键词，100字符以内）+ 5 条英文 Bullet Points（每条突出一个卖点，口语化、有转化力）；
                2. 不要编造卖点之外的功能参数；
                3. 直接输出文案，不要解释。"""

    resp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,  # 文案类任务保留一点发散度
    )
    return resp.choices[0].message.content
