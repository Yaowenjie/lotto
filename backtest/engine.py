"""
Backtest Engine — 回测引擎
使用滑动窗口: 用前N期预测第N+1期，验证命中率
"""
from typing import List, Dict, Any, Tuple
from collections import Counter
from predictor.engine import PredictorEngine
from predictor.base import LotteryType


def match_ssq(pred: Dict, actual: Dict) -> Dict[str, int]:
    """计算双色球预测与实际匹配的号码数"""
    pred_red = set(pred["red"])
    actual_red = set(actual["red"])
    matched_red = len(pred_red & actual_red)
    matched_blue = 1 if pred["blue"] == actual["blue"] else 0
    return {"red": matched_red, "blue": matched_blue}


def match_dlt(pred: Dict, actual: Dict) -> Dict[str, int]:
    """计算大乐透预测与实际匹配的号码数"""
    pred_front = set(pred["front"])
    actual_front = set(actual["front"])
    matched_front = len(pred_front & actual_front)
    pred_back = set(pred["back"])
    actual_back = set(actual["back"])
    matched_back = len(pred_back & actual_back)
    return {"front": matched_front, "back": matched_back}


def calc_ssq_rank(red: int, blue: int) -> int:
    """双色球中奖等级 (0=不中)"""
    if red == 6 and blue == 1:
        return 1  # 一等奖
    elif red == 6 and blue == 0:
        return 2  # 二等奖
    elif red == 5 and blue == 1:
        return 3  # 三等奖
    elif red == 5 and blue == 0 or red == 4 and blue == 1:
        return 4  # 四等奖
    elif red == 4 and blue == 0 or red == 3 and blue == 1:
        return 5  # 五等奖
    elif red == 3 and blue == 0 or red == 2 and blue == 1 or red == 1 and blue == 1 or red == 0 and blue == 1:
        return 6  # 六等奖
    return 0


def calc_dlt_rank(front: int, back: int) -> int:
    """大乐透中奖等级 (0=不中)"""
    if front == 5 and back == 2:
        return 1  # 一等奖
    elif front == 5 and back == 1:
        return 2  # 二等奖
    elif front == 5 and back == 0 or front == 4 and back == 2:
        return 3  # 三等奖
    elif front == 4 and back == 1 or front == 3 and back == 2:
        return 4  # 四等奖
    elif front == 4 and back == 0 or front == 3 and back == 1 or front == 2 and back == 2:
        return 5  # 五等奖
    elif front == 3 and back == 0 or front == 1 and back == 2 or front == 2 and back == 1 or front == 0 and back == 2:
        return 6  # 六等奖
    elif front == 2 and back == 0 or front == 1 and back == 1 or front == 0 and back == 1:
        return 7  # 七等奖
    elif front == 1 and back == 0 or front == 0 and back == 0:
        return 8  # 八等奖
    return 0


class BacktestEngine:
    """回测引擎"""

    def __init__(self, lottery_type: str):
        self.lottery_type = lottery_type
        self.engine = PredictorEngine(lottery_type)

    def run(self, history: List[Dict], strategy_key: str,
            lookback: int = 30, predict_ahead: int = 1,
            params: Dict = None) -> Dict[str, Any]:
        """
        回测: 用 [0:lookback] 预测 [lookback], 用 [1:lookback+1] 预测 [lookback+1], ...
        最多回测 predict_ahead 期（默认1，即只测下一期）
        返回详细结果和统计
        """
        params = params or {}
        if len(history) < lookback + predict_ahead:
            return {"error": f"历史数据不足，需要至少 {lookback + predict_ahead} 期"}

        detail_records = []
        red_hit_dist = Counter()
        front_hit_dist = Counter()
        back_hit_dist = Counter()
        rank_dist = Counter()
        total_bets = 0

        # 取最新N期往历史方向回测
        # history[0] = 最新一期，history[-1] = 最旧一期
        # 从 lookback 位置开始往前推（即用 lookback 期预测第 lookback 期）
        # 实际: 用 history[i-lookback:i] 预测 history[i]，i 从 lookback 到 len(history)-1

        max_tests = min(predict_ahead, len(history) - lookback)
        blue_hits = 0
        for offset in range(max_tests):
            train_end = len(history) - offset
            train_start = train_end - lookback
            if train_start < 0:
                break
            train_history = history[train_start:train_end]
            actual = history[train_end - 1]

            pred = self.engine.predict(strategy_key, train_history, **params)
            total_bets += 1

            if self.lottery_type == LotteryType.SSQ:
                m = match_ssq(pred, actual)
                red_hit_dist[m["red"]] += 1
                blue_hits += m["blue"]
                rank = calc_ssq_rank(m["red"], m["blue"])
                rank_dist[rank] += 1
                detail_records.append({
                    "expect": actual.get("expect", f"#{offset}"),
                    "predicted": pred["display"],
                    "actual": "红球:" + " ".join(f"{n:02d}" for n in actual['red']) + f" 蓝球:{actual['blue']:02d}",
                    "red_hit": m["red"],
                    "blue_hit": m["blue"],
                    "rank": rank if rank > 0 else "未中奖"
                })
            else:
                m = match_dlt(pred, actual)
                front_hit_dist[m["front"]] += 1
                back_hit_dist[m["back"]] += 1
                rank = calc_dlt_rank(m["front"], m["back"])
                rank_dist[rank] += 1
                detail_records.append({
                    "expect": actual.get("expect", f"#{offset}"),
                    "predicted": pred["display"],
                    "actual": "前区:" + " ".join(f"{n:02d}" for n in actual['front']) + " 后区:" + " ".join(f"{n:02d}" for n in actual['back']),
                    "front_hit": m["front"],
                    "back_hit": m["back"],
                    "rank": rank if rank > 0 else "未中奖"
                })

        # 汇总
        summary = {
            "total_bets": total_bets,
            "lottery_type": self.lottery_type,
            "strategy_key": strategy_key,
            "lookback": lookback,
            "rank_distribution": dict(rank_dist),
            "strategy_params": params,
        }

        if self.lottery_type == LotteryType.SSQ:
            summary["red_hit_distribution"] = dict(red_hit_dist)
            summary["blue_hit_rate"] = sum(1 for d in detail_records if d.get("blue_hit")) / max(total_bets, 1)
        else:
            summary["front_hit_distribution"] = dict(front_hit_dist)
            summary["back_hit_distribution"] = dict(back_hit_dist)

        return {
            "summary": summary,
            "details": detail_records
        }

    def batch_backtest(self, history: List[Dict], strategy_keys: List[str],
                       lookback: int = 30, predict_ahead: int = 10,
                       params_map: Dict[str, Dict] = None) -> Dict[str, Dict]:
        """对多个策略同时回测对比"""
        params_map = params_map or {}
        results = {}
        for key in strategy_keys:
            params = params_map.get(key, {})
            result = self.run(history, key, lookback=lookback,
                              predict_ahead=predict_ahead, params=params)
            results[key] = result
        return results
