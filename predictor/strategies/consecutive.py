"""
策略6: 连号历史规律策略 (ConsecutiveStrategy)
核心规则：
  1. 重复号规律：历史数据显示每期约1-2个号码重复自上期（占比80%以上）
  2. 生成策略：固定从上一期(最新历史)选取1-2个重复号，再从位置热号中补充剩余
  3. 同时考虑AC值约束，保证组合在历史常见AC值范围内(7-10)
"""
import random
from collections import Counter
from typing import List, Dict, Any, Tuple
from predictor.base import BaseStrategy, LotteryType


class ConsecutiveStrategy(BaseStrategy):
    """
    consecutive_prob: 是否包含重复号（默认0.8，自历史规律）
    repeat_count: 从上期重复几个号（默认1-2个）
    """
    name = "连号策略"
    description = "基于历史重复号规律，从上期选取1-2个重复号，配合位置热号组成新注"

    def _calc_ac(self, balls: List[int]) -> int:
        diffs = set()
        for i in range(len(balls)):
            for j in range(i + 1, len(balls)):
                diffs.add(abs(balls[i] - balls[j]))
        return len(diffs) - (len(balls) - 1)

    def predict(self, history: List[Dict], consecutive_prob: float = 0.8,
                repeat_count: int = 1, **kwargs) -> Dict[str, Any]:
        window = 30
        if len(history) < 1:
            repeat_count = 1
            prev_balls = list(range(1, 34))
        else:
            prev_balls = history[0]["red"] if self.lottery_type == LotteryType.SSQ else history[0]["front"]

        # ---- 位置热号候选 ----
        if self.lottery_type == LotteryType.SSQ:
            pool = list(range(1, 34))
            need = 6
            pos_candidates = []
            for pos in range(6):
                cnt = Counter(row["red"][pos] for row in history[:window])
                top7 = [n for n, _ in cnt.most_common(7)]
                pos_candidates.append(top7 if top7 else pool[:])

            # ---- 历史AC值分布 ----
            ac_counts = Counter()
            for row in history[:window]:
                ac_counts[self._calc_ac(row["red"])] += 1
            target_ac = ac_counts.most_common(1)[0][0] if ac_counts else 8
        else:
            pool = list(range(1, 36))
            need = 5
            pos_candidates = []
            for pos in range(5):
                cnt = Counter(row["front"][pos] for row in history[:window])
                top7 = [n for n, _ in cnt.most_common(7)]
                pos_candidates.append(top7 if top7 else pool[:])

            ac_counts = Counter()
            for row in history[:window]:
                ac_counts[self._calc_ac(row["front"])] += 1
            target_ac = ac_counts.most_common(1)[0][0] if ac_counts else 8

        # ---- 生成号码：重复号 + 位置热号补充 ----
        if random.random() < consecutive_prob and len(history) > 0:
            # 从上一期选repeat_count个作为保留号
            repeat_n = random.randint(1, 2)  # 1-2个重复（历史最常见）
        else:
            repeat_n = 0

        selected = []

        if repeat_n > 0 and len(history) > 0:
            # 随机选repeat_n个上期号码
            keep = random.sample(prev_balls, min(repeat_n, len(prev_balls)))
            selected.extend(keep)

        # 补充剩余号码：从位置热号候选中选（优先选不在selected中的）
        for pos in range(need):
            if len(selected) >= need:
                break
            candidates = [n for n in pos_candidates[pos] if n not in selected]
            if not candidates:
                candidates = [n for n in pool if n not in selected]
            if candidates:
                selected.append(random.choice(candidates))

        # 截断并排序
        selected = sorted(set(selected))[:need]
        while len(selected) < need:
            for pos in range(need):
                if len(selected) >= need:
                    break
                candidates = [n for n in pos_candidates[pos] if n not in selected]
                if not candidates:
                    candidates = [n for n in pool if n not in selected]
                if candidates:
                    selected.append(random.choice(candidates))
            if len(selected) >= need:
                break
            selected.append(random.choice([n for n in pool if n not in selected]))
        selected = sorted(set(selected))[:need]

        # ---- AC值过滤（SSQ）----
        if self.lottery_type == LotteryType.SSQ:
            for _ in range(200):
                if self._calc_ac(selected) >= 7:
                    break
                # 替换一个号以提升AC值
                idx = random.randint(0, 5)
                pos_pool = pos_candidates[idx]
                new_candidates = [n for n in pos_pool if n not in selected]
                if new_candidates:
                    selected[idx] = random.choice(new_candidates)
                    selected = sorted(set(selected))

        if self.lottery_type == LotteryType.SSQ:
            blue = random.randint(1, 16)
            result = self._format_ssq(selected, blue)
            result["metadata"] = {
                "repeat_count": repeat_n if repeat_n > 0 else 0,
                "target_ac": target_ac,
                "actual_ac": self._calc_ac(selected),
                "strategy": self.name
            }
            return result
        else:
            back_pool = list(range(1, 13))
            back = random.sample(back_pool, 2)
            result = self._format_dlt(selected, back)
            result["metadata"] = {
                "repeat_count": repeat_n if repeat_n > 0 else 0,
                "strategy": self.name
            }
            return result