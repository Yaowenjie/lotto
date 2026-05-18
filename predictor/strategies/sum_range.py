"""
策略4: 和值策略 (SumRangeStrategy)
核心规则：
  1. 统计历史和值分布，取最常见和值区间（center模式的均值±12）
  2. 在目标和值区间内，从位置热号候选中搜索组合
  3. 满足奇偶比例(2:4~4:2)和和值双重约束
"""
import random
from collections import Counter
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType


class SumRangeStrategy(BaseStrategy):
    """
    mode: center / low / high
    """
    name = "和值策略"
    description = "基于历史和值分布，在目标和值范围内从位置热号候选中搜索组合"

    def predict(self, history: List[Dict], mode: str = "center", **kwargs) -> Dict[str, Any]:
        window = 30

        def search_with_constraints(pool: List[int], need: int,
                                     min_sum: int, max_sum: int,
                                     pos_candidates: List[List[int]],
                                     max_attempts: int = 500) -> List[int]:
            """在和值约束+位置热号约束下搜索号码组合"""
            for _ in range(max_attempts):
                selected = []
                for pos in range(need):
                    candidates = [n for n in pos_candidates[min(pos, len(pos_candidates)-1)] if n in pool]
                    if not candidates:
                        candidates = pool[:]
                    selected.append(random.choice(candidates))
                if min_sum <= sum(selected) <= max_sum:
                    odds = sum(1 for n in selected if n % 2 == 1)
                    if 1 <= odds <= 5:  # 至少1个奇数
                        return selected
            return selected  # fallback

        if self.lottery_type == LotteryType.SSQ:
            # ---- 1. 位置热号候选 ----
            pos_candidates = []
            for pos in range(6):
                cnt = Counter(row["red"][pos] for row in history[:window])
                top7 = [n for n, _ in cnt.most_common(7)]
                pos_candidates.append(top7 if top7 else list(range(1, 34)))

            # ---- 2. 和值统计（近30期）----
            sums = [sum(row["red"]) for row in history[:window]]
            avg_sum = sum(sums) / len(sums) if sums else 100

            if mode == "low":
                target_sum = int(random.uniform(min(sums) if sums else 60, avg_sum - 10))
                min_sum, max_sum = max(40, target_sum - 12), target_sum + 8
            elif mode == "high":
                target_sum = int(random.uniform(avg_sum + 10, max(sums) if sums else 140))
                min_sum, max_sum = target_sum - 8, min(160, target_sum + 12)
            else:  # center
                min_sum, max_sum = int(avg_sum - 12), int(avg_sum + 12)

            pool = list(range(1, 34))
            selected = search_with_constraints(pool, 6, min_sum, max_sum, pos_candidates)

            blue = random.randint(1, 16)
            result = self._format_ssq(selected, blue)
            result["metadata"] = {
                "avg_sum": round(avg_sum, 1),
                "target_range": f"{min_sum}-{max_sum}",
                "actual_sum": sum(selected),
                "strategy": self.name
            }
            return result

        else:  # DLT
            front_sums = [sum(row["front"]) for row in history[:window]]
            avg_front_sum = sum(front_sums) / len(front_sums) if front_sums else 70

            if mode == "low":
                min_fs, max_fs = max(20, int(avg_front_sum - 20)), int(avg_front_sum - 5)
            elif mode == "high":
                min_fs, max_fs = int(avg_front_sum + 5), min(120, int(avg_front_sum + 20))
            else:
                min_fs, max_fs = int(avg_front_sum - 10), int(avg_front_sum + 10)

            front_pool = list(range(1, 36))
            front = []
            for _ in range(500):
                f = sorted(random.sample(front_pool, 5))
                if min_fs <= sum(f) <= max_fs:
                    odds = sum(1 for n in f if n % 2 == 1)
                    if 1 <= odds <= 4:
                        front = f
                        break
            if not front:
                front = sorted(random.sample(front_pool, 5))

            back_pool = list(range(1, 13))
            back = random.sample(back_pool, 2)

            result = self._format_dlt(front, back)
            result["metadata"] = {
                "avg_front_sum": round(avg_front_sum, 1),
                "front_sum_range": f"{min_fs}-{max_fs}",
                "strategy": self.name
            }
            return result