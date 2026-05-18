"""
双色球 (SSQ) 数据抓取 from 17500.cn
注意: limit >= 50 才有返回
"""
import re
import requests
from typing import List, Optional

SSQ_API = "https://www.17500.cn/api/chart/ssq/kjh"


def _session_headers(ref: str):
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"https://www.17500.cn/chart/{ref}",
        "X-Requested-With": "XMLHttpRequest"
    }


def _parse_ssq_row(td: str) -> dict:
    """从第5个td中解析奖号，格式: '10 11 15 19 29 30 + 10'"""
    text = td.strip()
    # 去掉 &nbsp; 和所有HTML标签
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # 格式: "10 11 15 19 29 30 + 10"
    parts = text.split("+")
    if len(parts) != 2:
        return None, None
    reds = [int(x.strip()) for x in parts[0].strip().split() if x.strip()]
    blue = int(parts[1].strip())
    if len(reds) != 6:
        return None, None
    return reds, blue


def fetch_ssq_history(limit: int = 100) -> List[dict]:
    """
    抓取双色球历史开奖数据。
    返回: [{"expect": "2025058", "date": "2025-05-25", "red": [10,11,15,19,29,30], "blue": 10}, ...]
    """
    if limit < 50:
        limit = 50  # API requires >= 50

    session = requests.Session()
    session.headers.update(_session_headers("ssq-kjh"))
    session.get("https://www.17500.cn/chart/ssq-kjh.html", timeout=10)

    resp = session.post(SSQ_API, data={"limit": limit}, timeout=15)
    resp.encoding = "utf-8"
    html = resp.text

    results = []
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    if not tbody_match:
        return results

    rows = re.findall(r"<tr>(.*?)</tr>", tbody_match.group(1), re.DOTALL)
    for row in rows:
        tds = re.findall(r"<td>(.*?)</td>", row, re.DOTALL)
        if len(tds) < 5:
            continue
        expect = tds[0].strip()
        if not re.match(r"^\d{7}$", expect):
            continue
        date_str = tds[1].strip()

        reds, blue = _parse_ssq_row(tds[8])  # TD[8] = 奖号
        if reds is None:
            continue

        results.append({
            "expect": expect,
            "date": date_str,
            "red": reds,
            "blue": blue
        })
    return results


def fetch_latest_ssq() -> Optional[dict]:
    """获取最新一期数据"""
    rows = fetch_ssq_history(50)
    return rows[0] if rows else None
