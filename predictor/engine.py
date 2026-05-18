"""
Predictor Engine — 加载策略、统一入口
"""
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType
from predictor.strategies.hot_cold import HotColdStrategy
from predictor.strategies.odd_even import OddEvenStrategy
from predictor.strategies.zone import ZoneStrategy
from predictor.strategies.sum_range import SumRangeStrategy
from predictor.strategies.digit_end import DigitEndStrategy
from predictor.strategies.consecutive import ConsecutiveStrategy
from predictor.strategies.ac_value import ACValueStrategy
from predictor.strategies.trend import TrendStrategy


ALL_STRATEGIES = {
    "hot_cold": HotColdStrategy,
    "odd_even": OddEvenStrategy,
    "zone": ZoneStrategy,
    "sum_range": SumRangeStrategy,
    "digit_end": DigitEndStrategy,
    "consecutive": ConsecutiveStrategy,
    "ac_value": ACValueStrategy,
    "trend": TrendStrategy,
}

STRATEGY_NAMES = {
    "hot_cold": "冷热号策略",
    "odd_even": "奇偶比例策略",
    "zone": "区间分布策略",
    "sum_range": "和值策略",
    "digit_end": "尾数策略",
    "consecutive": "连号策略",
    "ac_value": "AC值策略",
    "trend": "趋势策略",
}


class PredictorEngine:
    """预测引擎: 持有策略实例，生成预测"""

    def __init__(self, lottery_type: str):
        self.lottery_type = lottery_type
        self.strategies: Dict[str, BaseStrategy] = {}
        for key, cls in ALL_STRATEGIES.items():
            self.strategies[key] = cls(lottery_type)

    def predict(self, strategy_key: str, history: List[Dict],
                **params) -> Dict[str, Any]:
        if strategy_key not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_key}")
        strategy = self.strategies[strategy_key]
        return strategy.predict(history, **params)

    def generate_batch(self, strategy_key: str, history: List[Dict],
                       count: int = 5, **params) -> List[Dict[str, Any]]:
        """批量生成多组预测号码"""
        results = []
        for i in range(count):
            result = self.predict(strategy_key, history, **params)
            results.append(result)
        return results

    @staticmethod
    def get_strategy_params(strategy_key: str) -> List[Dict[str, Any]]:
        """返回策略的可配置参数定义（供UI渲染）"""
        params_map = {
            "hot_cold": [
                {"name": "mode", "label": "模式", "type": "select",
                 "options": ["balanced", "hot", "cold"], "default": "balanced"},
                {"name": "window", "label": "参考期数", "type": "slider", "min": 10, "max": 50, "default": 20},
            ],
            "odd_even": [
                {"name": "mode", "label": "模式", "type": "select",
                 "options": ["most_common", "specific"], "default": "most_common"},
                {"name": "target_ratio", "label": "目标比例", "type": "text", "default": "3:3"},
            ],
            "zone": [
                {"name": "zones", "label": "区间数量", "type": "slider", "min": 2, "max": 5, "default": 3},
                {"name": "min_per_zone", "label": "每区最少号码", "type": "slider", "min": 1, "max": 3, "default": 1},
            ],
            "sum_range": [
                {"name": "mode", "label": "和值区间", "type": "select",
                 "options": ["center", "low", "high"], "default": "center"},
            ],
            "digit_end": [
                {"name": "min_distinct", "label": "最少不同尾数", "type": "slider", "min": 2, "max": 5, "default": 3},
            ],
            "consecutive": [
                {"name": "consecutive_prob", "label": "重复号概率", "type": "slider", "min": 0.0, "max": 1.0, "default": 0.8},
                {"name": "repeat_count", "label": "重复号个数", "type": "slider", "min": 1, "max": 2, "default": 1},
            ],
            "ac_value": [
                {"name": "mode", "label": "模式", "type": "select",
                 "options": ["most_common", "high", "low"], "default": "most_common"},
            ],
            "trend": [
                {"name": "window", "label": "分析期数", "type": "slider", "min": 10, "max": 50, "default": 30},
            ],
        }
        return params_map.get(strategy_key, [])
