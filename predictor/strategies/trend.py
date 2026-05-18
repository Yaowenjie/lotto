"""
策略8: 趋势策略 (TrendStrategy)
核心规则（多因子评分模型）：
  1. 位置因子（权重50%）：每位置历史最热号码得分高
  2. 频率因子（权重30%）：近30期出现次数多的号码加分
  3. 遗漏因子（权重20%）：遗漏10-25期的中等遗漏号加分（过热过冷都减分）
  4. 最终按综合评分排序，从Top候选中随机选6个（带随机性避免固定）
  5. 满足奇偶比例约束(2:4~4:2)
"""
import random
from collections import Counter
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType


class TrendStrategy(BaseStrategy):
    """
    window: 分析最近多少期 (默认30)
    """
    name = "趋势策略"
    description = "多因子评分模型：位置热度×频率×遗漏期数综合评分，从高分候选中选号"

    def predict(self, history: List[Dict], window: int = 30,
                **kwargs) -> Dict[str, Any]:
        window = int(window)
        recent = history[:window]

        if self.lottery_type == LotteryType.SSQ:
            max_num = 33
            need = 6

            # ---- 1. 位置因子（每位置Top候选）----
            pos_candidates = []
            for pos in range(6):
                cnt = Counter(row["red"][pos] for row in recent)
                top5 = [n for n, _ in cnt.most_common(5)]
                pos_candidates.append(top5 if top5 else list(range(1, 34)))

            # ---- 2. 全局频率因子 ----
            freq_count = Counter()
            for row in recent:
                freq_count.update(row["red"])

            # ---- 3. 遗漏因子 ----
            missing = {}
            for n in range(1, max_num + 1):
                miss = 0
                for row in recent:
                    if n in row["red"]:
                        break
                    miss += 1
                if miss == len(recent):
                    miss = len(recent) + random.randint(0, 5)
                missing[n] = miss

            # ---- 4. 多因子综合评分 ----
            scores = {}
            top3_per_pos = [set(pos_candidates[pos][:3]) for pos in range(6)]

            for n in range(1, max_num + 1):
                # 位置因子：n在各位置出现次数（归一化到0-1）
                pos_score = sum(1 for pos_list in pos_candidates if n in pos_list) / 6.0

                # 频率因子：出现次数（归一化到0-1）
                max_freq = max(freq_count.values()) if freq_count else 1
                freq_score = freq_count.get(n, 0) / max_freq

                # 遗漏因子：中等遗漏最优(10-25期)，太新或太久都不好
                miss = missing.get(n, window)
                if 10 <= miss <= 25:
                    miss_score = 1.0
                elif miss < 5:
                    miss_score = 0.3  # 太热了（刚出过）
                elif miss > window:
                    miss_score = 0.5  # 太冷了（遗漏太久）
                else:
                    miss_score = 0.7

                # 综合评分：位置50% + 频率30% + 遗漏20%
                scores[n] = pos_score * 0.5 + freq_score * 0.3 + miss_score * 0.2

            # ---- 5. 生成号码：从Top候选中选取 ----
            sorted_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
            top_candidates = sorted_nums[:need + 5]  # 前11个作为候选池

            selected = []
            for _ in range(200):
                if len(selected) >= need:
                    break
                candidates = [n for n in top_candidates if n not in selected]
                if not candidates:
                    candidates = [n for n in sorted_nums if n not in selected]
                if candidates:
                    chosen = random.choice(candidates[:min(5, len(candidates))])
                    selected.append(chosen)

            # 奇偶约束
            for attempt in range(200):
                odds = sum(1 for n in selected if n % 2 == 1)
                if 2 <= odds <= 4:
                    break
                # 替换一个奇偶不合适的号
                idx = random.randint(0, len(selected)-1)
                rest = [n for n in sorted_nums if n not in selected and n not in [selected[idx]]]
                if rest:
                    selected[idx] = random.choice(rest[:5])

            selected = sorted(set(selected))[:need]
            while len(selected) < need:
                remaining = [n for n in range(1, 34) if n not in selected]
                if remaining:
                    selected.append(random.choice(remaining))
                else:
                    break
            selected = sorted(selected)[:need]

            blue = random.randint(1, 16)
            result = self._format_ssq(selected, blue)
            result["metadata"] = {
                "window": window,
                "top_scores": {n: round(scores[n], 2) for n in selected[:5]},
                "strategy": self.name
            }
            return result

        else:  # DLT
            max_num = 35
            need = 5

            pos_candidates = []
            for pos in range(5):
                cnt = Counter(row["front"][pos] for row in recent)
                top5 = [n for n, _ in cnt.most_common(5)]
                pos_candidates.append(top5 if top5 else list(range(1, 36)))

            freq_count = Counter()
            for row in recent:
                freq_count.update(row["front"])

            scores = {}
            for n in range(1, max_num + 1):
                pos_score = sum(1 for pos_list in pos_candidates if n in pos_list) / 5.0
                max_freq = max(freq_count.values()) if freq_count else 1
                freq_score = freq_count.get(n, 0) / max_freq
                miss = 0
                for row in recent:
                    if n in row["front"]:
                        break
                    miss += 1
                if 8 <= miss <= 20:
                    miss_score = 1.0
                elif miss < 4:
                    miss_score = 0.3
                else:
                    miss_score = 0.5
                scores[n] = pos_score * 0.5 + freq_score * 0.3 + miss_score * 0.2

            sorted_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
            top_candidates = sorted_nums[:need + 4]

            front = []
            for _ in range(200):
                if len(front) >= need:
                    break
                candidates = [n for n in top_candidates if n not in front]
                if not candidates:
                    candidates = [n for n in sorted_nums if n not in front]
                if candidates:
                    front.append(random.choice(candidates[:min(4, len(candidates))]))

            front = sorted(set(front))[:need]
            while len(front) < need:
                remaining = [n for n in range(1, 36) if n not in front]
                if remaining:
                    front.append(random.choice(remaining))
                else:
                    break

            back_pool = list(range(1, 13))
            back = random.sample(back_pool, 2)

            result = self._format_dlt(front, back)
            result["metadata"] = {
                "window": window,
                "strategy": self.name
            }
            return result