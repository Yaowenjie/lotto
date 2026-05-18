"""
策略2: 奇偶比例策略 (OddEvenStrategy)
核心规则：
  1. 分析历史奇偶比分布，选取最常见的奇偶比例作为目标（4:2或3:3）
  2. 选号时从每位置历史最热Top7候选中搜索满足目标奇偶比的组合
  3. 放宽匹配要求：精确相等优先，±1也接受
"""
import random
from collections import Counter
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType


class OddEvenStrategy(BaseStrategy):
    """
    mode: most_common / specific
    target_ratio: 目标奇偶比，如 "3:3"、"4:2"
    """
    name = "奇偶比例策略"
    description = "基于历史最常见奇偶比，从位置热号候选中搜索满足比例的号码组合"

    def predict(self, history: List[Dict], mode: str = "most_common",
                target_ratio: str = "3:3", **kwargs) -> Dict[str, Any]:
        window = 30
        recent = history[:window]

        if self.lottery_type == LotteryType.SSQ:
            # ---- 1. 历史奇偶比分布 ----
            ratio_count = Counter()
            for row in recent:
                odds = sum(1 for n in row["red"] if n % 2 == 1)
                ratio_count[f"{odds}:{6-odds}"] += 1

            if mode == "most_common":
                top_ratio = ratio_count.most_common(1)[0][0]
            else:
                top_ratio = target_ratio
            odd_target, even_target = map(int, top_ratio.split(":"))

            # ---- 2. 每位置热号候选 ----
            pos_candidates = []
            for pos in range(6):
                cnt = Counter(row["red"][pos] for row in recent)
                top7 = [n for n, _ in cnt.most_common(7)]
                pos_candidates.append(top7 if top7 else list(range(1, 34)))

            # ---- 3. 搜索满足奇偶比的组合 ----
            selected = None
            for _ in range(500):
                reds = []
                for pos in range(6):
                    reds.append(random.choice(pos_candidates[pos]))
                odds_count = sum(1 for n in reds if n % 2 == 1)
                if odds_count == odd_target:
                    selected = sorted(reds)
                    break

            # 备选：允许±1的误差
            if selected is None:
                for _ in range(500):
                    reds = []
                    for pos in range(6):
                        reds.append(random.choice(pos_candidates[pos]))
                    odds_count = sum(1 for n in reds if n % 2 == 1)
                    if abs(odds_count - odd_target) <= 1:
                        selected = sorted(reds)
                        break

            # 最终备选：完全随机
            if selected is None:
                selected = sorted(random.sample(range(1, 34), 6))

            blue = random.randint(1, 16)
            result = self._format_ssq(selected, blue)
            result["metadata"] = {
                "target_ratio": top_ratio,
                "history_distribution": dict(ratio_count.most_common(5)),
                "strategy": self.name
            }
            return result

        else:  # DLT
            ratio_count = Counter()
            for row in recent:
                odds = sum(1 for n in row["front"] if n % 2 == 1)
                ratio_count[f"{odds}:{5-odds}"] += 1

            if mode == "most_common":
                top_ratio = ratio_count.most_common(1)[0][0]
            else:
                top_ratio = target_ratio
            odd_target, even_target = map(int, top_ratio.split(":"))

            pos_candidates = []
            for pos in range(5):
                cnt = Counter(row["front"][pos] for row in recent)
                top7 = [n for n, _ in cnt.most_common(7)]
                pos_candidates.append(top7 if top7 else list(range(1, 36)))

            front = None
            for _ in range(500):
                f = []
                for pos in range(5):
                    f.append(random.choice(pos_candidates[pos]))
                odds_count = sum(1 for n in f if n % 2 == 1)
                if odds_count == odd_target:
                    front = sorted(f)
                    break
            if front is None:
                for _ in range(500):
                    f = []
                    for pos in range(5):
                        f.append(random.choice(pos_candidates[pos]))
                    odds_count = sum(1 for n in f if n % 2 == 1)
                    if abs(odds_count - odd_target) <= 1:
                        front = sorted(f)
                        break
            if front is None:
                front = sorted(random.sample(range(1, 36), 5))

            back = list(range(1, 13))

            result = self._format_dlt(front, random.sample(back, 2))
            result["metadata"] = {
                "target_ratio": top_ratio,
                "history_distribution": dict(ratio_count.most_common(5)),
                "strategy": self.name
            }
            return result