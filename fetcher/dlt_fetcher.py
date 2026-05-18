"""
大乐透 (DLT) 数据抓取 from 17500.cn
注意: limit >= 50 且需要 week=9, z=1, act=kjh 参数
"""
import re
import requests
from typing import List, Optional

DLT_API = "https://www.17500.cn/api/chart/dlt/kjh"


def _session_headers(ref: str):
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"https://www.17500.cn/chart/{ref}",
        "X-Requested-With": "XMLHttpRequest"
    }


def _parse_dlt_row(td: str) -> dict:
    """从第5个td中解析奖号，格式: '02 04 16 23 35 + 06 11'"""
    text = td.strip()
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = text.split("+")
    if len(parts) != 2:
        return None, None
    front = [int(x.strip()) for x in parts[0].strip().split() if x.strip()]
    back = [int(x.strip()) for x in parts[1].strip().split() if x.strip()]
    if len(front) != 5 or len(back) != 2:
        return None, None
    return front, back


def fetch_dlt_history(limit: int = 100) -> List[dict]:
    """
    抓取大乐透历史开奖数据。
    返回: [{"expect": "2026005", "date": "2026-01-12",
            "front": [2,4,16,23,35], "back": [6,11]}, ...]
    """
    if limit < 50:
        limit = 50

    session = requests.Session()
    session.headers.update(_session_headers("dlt-kjh"))
    session.get("https://www.17500.cn/chart/dlt-kjh.html", timeout=10)

    payload = {"limit": limit, "week": 9, "z": 1, "act": "kjh"}
    resp = session.post(DLT_API, data=payload, headers=_session_headers("dlt-kjh"), timeout=15)
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

        front, back = _parse_dlt_row(tds[8])  # TD[8] = 奖号
        if front is None:
            continue

        results.append({
            "expect": expect,
            "date": date_str,
            "front": front,
            "back": back
        })
    return results


def fetch_latest_dlt() -> Optional[dict]:
    """获取最新一期大乐透数据"""
    rows = fetch_dlt_history(50)
    return rows[0] if rows else None
