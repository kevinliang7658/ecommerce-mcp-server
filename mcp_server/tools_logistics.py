"""
工具二：物流轨迹查询（mock 数据版）

跨境电商客服最高频的问题就是"我的包裹到哪了"。
大模型连你的物流系统都看不到，更不可能知道某个单号的轨迹，
所以把"查物流"做成工具，模型需要时自己调用。

mock 说明：内置两个假单号演示。真实项目把 query() 里的字典查询
换成调 17TRACK / 快递鸟 / 自有物流中台的 HTTP API 即可。
"""

# mock 物流数据库：单号 -> 轨迹列表（时间倒序，最新在最前）
MOCK_LOGISTICS = {
    "YT10001": [
        {"time": "2025-07-24 14:20", "status": "【上海】已签收，签收人：本人"},
        {"time": "2025-07-24 09:05", "status": "【上海】派送中，快递员：张师傅 138****0000"},
        {"time": "2025-07-22 18:40", "status": "【上海】到达上海转运中心"},
        {"time": "2025-07-20 03:15", "status": "【洛杉矶】国际航班起飞"},
        {"time": "2025-07-18 10:00", "status": "【洛杉矶】海外仓已发货"},
    ],
    "YT10002": [
        {"time": "2025-07-25 08:30", "status": "【深圳】清关完成，转国内派送"},
        {"time": "2025-07-23 16:10", "status": "【深圳】到达中国口岸，等待清关"},
        {"time": "2025-07-19 11:20", "status": "【法兰克福】国际航班起飞"},
        {"time": "2025-07-17 09:00", "status": "【法兰克福】海外仓已发货"},
    ],
}


def query(tracking_no: str) -> str:
    """
    按单号查询物流轨迹。

    :param tracking_no: 物流单号，如 YT10001
    :return: 轨迹的中文描述；单号不存在时给出明确提示
    """
    tracking_no = tracking_no.upper().strip()
    tracks = MOCK_LOGISTICS.get(tracking_no)
    if tracks is None:
        # 查不到也要返回"有用的提示"，不能抛异常——异常会让大模型不知道怎么回复用户
        return f"未查询到单号 {tracking_no} 的物流信息，请确认单号是否正确。（演示单号：YT10001、YT10002）"

    latest = tracks[0]
    lines = [f"单号 {tracking_no} 最新状态：{latest['status']}", "完整轨迹："]
    lines += [f"  {t['time']}  {t['status']}" for t in tracks]
    return "\n".join(lines)
