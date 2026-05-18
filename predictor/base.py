"""
Base class for all prediction strategies.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import random


class LotteryType:
    SSQ = "ssq"   # 双色球
    DLT = "dlt"   # 大乐透


class BaseStrategy(ABC):
    """Abstract base class for lottery prediction strategies."""

    name: str = "BaseStrategy"
    description: str = ""

    def __init__(self, lottery_type: str):
        self.lottery_type = lottery_type

    @abstractmethod
    def predict(self, history: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        基于历史数据生成预测号码。
        history: 最新到最旧的历史开奖列表
        返回: {"balls": [...], "metadata": {...}}
        """
        pass

    def _sort_balls(self, balls: List[int]) -> List[int]:
        return sorted(balls)

    def _unique_balls(self, balls: List[int]) -> List[int]:
        seen = set()
        result = []
        for b in balls:
            if b not in seen:
                seen.add(b)
                result.append(b)
        return result

    def _format_ssq(self, red: List[int], blue: int) -> Dict[str, Any]:
        return {
            "red": self._sort_balls(red),
            "blue": blue,
            "display": "红球: " + " ".join(f"{n:02d}" for n in red) + f" 蓝球: {blue:02d}"
        }

    def _format_dlt(self, front: List[int], back: List[int]) -> Dict[str, Any]:
        return {
            "front": self._sort_balls(front),
            "back": self._sort_balls(back),
            "display": "前区: " + " ".join(f"{n:02d}" for n in front) + " 后区: " + " ".join(f"{n:02d}" for n in back)
        }
