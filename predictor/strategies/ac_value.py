"""
策略7: AC值策略 (ACValueStrategy)
核心规则（重新设计）：
  1. 不再以AC值为硬过滤条件（历史数据证明AC过滤会降低命中率）
  2. 核心：位置热号优先（每位置Top7）+ 和值范围约束 + 奇偶比例
  3. AC值仅作为元数据显示，不参与选号过滤
  4. 额外约束：号码分散度——6个号码中至少覆盖4个不同尾数
"""
import random
from collections import Counter
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType


class ACValueStrategy(BaseStrategy):
    """
    mode: most_common(默认) / high / low
    """
    name = "AC值策略"
    description = "位置热号优先，结合和值范围+奇偶比例+尾数分散度约束生成号码"

    def _calc_ac(self, balls: List[int]) -> int:
        diffs = set()
        for i in range(len(balls)):
            for j in range(i + 1, len(balls)):
                diffs.add(abs(balls[i] - balls[j]))
        return len(diffs) - (len(balls) - 1)

    def predict(self, history: List[Dict], mode: str = "most_common",
                **kwargs) -> Dict[str, Any]:
        window = 30

        if self.lottery_type == LotteryType.SSQ:
            # ---- 1. 位置热号候选 ----
            pos_candidates = []
            for pos in range(6):
                cnt = Counter(row["red"][pos] for row in history[:window])
                top7 = [n for n, _ in cnt.most_common(7)]
                pos_candidates.append(top7 if top7 else list(range(1, 34)))

            # ---- 2. 和值范围 ----
            sums = [sum(row["red"]) for row in history[:window]]
            avg_sum = sum(sums) / len(sums) if sums else 100
            if mode == "low":
                min_sum, max_sum = max(60, int(avg_sum - 20)), int(avg_sum - 5)
            elif mode == "high":
                min_sum, max_sum = int(avg_sum + 5), min(150, int(avg_sum + 20))
            else:
                min_sum, max_sum = int(avg_sum - 15), int(avg_sum + 15)

            # ---- 3. 搜索满足多重约束的组合 ----
            result_balls = None
            for _ in range(1000):
                reds = []
                for pos in range(6):
                    reds.append(random.choice(pos_candidates[pos]))
                reds = sorted(set(reds))

                # 和值约束
                if not (min_sum <= sum(reds) <= max_sum):
                    continue
                # 奇偶约束: 2:4 ~ 4:2
                odds = sum(1 for n in reds if n % 2 == 1)
                if not (2 <= odds <= 4):
                    continue
                # 尾数分散度: 至少4种不同尾数
                distinct_tails = len(set(n % 10 for n in reds))
                if distinct_tails < 4:
                    continue

                result_balls = reds
                break

            # 备选：放宽约束
            if result_balls is None:
                for _ in range(500):
                    reds = sorted(set([random.choice(pos_candidates[pos]) for pos in range(6)]))
                    if len(reds) < 4:
                        reds = sorted(random.sample(range(1, 34), 6))
                    odds = sum(1 for n in reds if n % 2 == 1)
                    if 1 <= odds <= 5:
                        result_balls = reds
                        break

            if result_balls is None:
                result_balls = sorted(random.sample(range(1, 34), 6))

            blue = random.randint(1, 16)
            result = self._format_ssq(result_balls, blue)
            result["metadata"] = {
                "mode": mode,
                "avg_sum": round(avg_sum, 1),
                "sum_range": f"{min_sum}-{max_sum}",
                "actual_ac": self._calc_ac(result_balls),
                "distinct_tails": len(set(n % 10 for n in result_balls)),
                "strategy": self.name
            }
            return result

        else:  # DLT
            pos_candidates = []
            for pos in range(5):
                cnt = Counter(row["front"][pos] for row in history[:window])
                top7 = [n for n, _ in cnt.most_common(7)]
                pos_candidates.append(top7 if top7 else list(range(1, 36)))

            sums = [sum(row["front"]) for row in history[:window]]
            avg_sum = sum(sums) / len(sums) if sums else 70

            front = None
            for _ in range(1000):
                f = sorted(set([random.choice(pos_candidates[pos]) for pos in range(5)]))
                if len(f) < 3:
                    continue
                if not (int(avg_sum - 15) <= sum(f) <= int(avg_sum + 15)):
                    continue
                odds = sum(1 for n in f if n % 2 == 1)
                if 1 <= odds <= 4:
                    front = f
                    break

            if front is None:
                front = sorted(random.sample(range(1, 36), 5))

            back = sorted(random.sample(range(1, 13), 2))
            result = self._format_dlt(front, back)
            result["metadata"] = {
                "mode": mode,
                "actual_ac": self._calc_ac(front),
                "strategy": self.name
            }
            return result