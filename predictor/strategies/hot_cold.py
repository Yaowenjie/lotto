"""
策略1: 冷热号策略 (HotColdStrategy)
基于近N期出现频率，区分热号/冷号/均衡模式
"""
import random
from collections import Counter
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType


class HotColdStrategy(BaseStrategy):
    """
    mode: hot / cold / balanced
    window: 参考期数 (默认20)
    """
    name = "冷热号策略"
    description = "基于近N期出现频率，热号=高频，冷号=低频/遗漏"

    def predict(self, history: List[Dict], mode: str = "balanced",
                window: int = 20, **kwargs) -> Dict[str, Any]:
        window = int(window)
        recent = history[:window]
        count = Counter()

        if self.lottery_type == LotteryType.SSQ:
            for row in recent:
                for n in row["red"]:
                    count[n] += 1
                count[f"blue_{row['blue']}"] += 1
            hot_reds = [n for n in range(1, 34) if count[n] > 0]
            hot_reds.sort(key=lambda x: count[x], reverse=True)
            cold_reds = [n for n in range(1, 34) if count[n] == 0 or count[n] <= 1]
            cold_reds.sort(key=lambda x: count[x])

            if mode == "hot":
                selected = hot_reds[:6]
            elif mode == "cold":
                selected = cold_reds[:6]
            else:  # balanced
                n_hot = random.randint(3, 4)
                n_cold = 6 - n_hot
                selected = hot_reds[:n_hot] + cold_reds[:n_cold]
                random.shuffle(selected)

            selected = self._unique_balls(selected)[:6]
            while len(selected) < 6:
                remaining = [n for n in range(1, 34) if n not in selected]
                selected.append(random.choice(remaining))

            # 蓝球: hot取最热，cold取最冷，balanced从Top3随机
            blue_counts = [(n, count[f"blue_{n}"]) for n in range(1, 17)]
            if mode == "hot":
                blue_counts.sort(key=lambda x: x[1], reverse=True)
                blue = blue_counts[0][0]
            elif mode == "cold":
                blue_counts.sort(key=lambda x: x[1])
                blue = blue_counts[0][0]
            else:  # balanced: 从前3热号中随机
                blue_counts.sort(key=lambda x: x[1], reverse=True)
                blue = random.choice(blue_counts[:3])[0]

            result = self._format_ssq(selected, blue)
            result["metadata"] = {
                "mode": mode,
                "window": window,
                "top_hot": hot_reds[:6],
                "cold_missing": cold_reds[:6],
                "strategy": self.name
            }
            return result

        else:  # DLT
            for row in recent:
                for n in row["front"]:
                    count[n] += 1
                for n in row["back"]:
                    count[f"back_{n}"] += 1

            front_hot = [n for n in range(1, 36) if count[n] > 0]
            front_hot.sort(key=lambda x: count[x], reverse=True)
            front_cold = [n for n in range(1, 36) if count[n] == 0 or count[n] <= 1]
            front_cold.sort(key=lambda x: count[x])

            if mode == "hot":
                front = front_hot[:5]
            elif mode == "cold":
                front = front_cold[:5]
            else:
                n_hot = random.randint(2, 3)
                front = front_hot[:n_hot] + front_cold[:(5 - n_hot)]
                random.shuffle(front)

            front = self._unique_balls(front)[:5]
            while len(front) < 5:
                remaining = [n for n in range(1, 36) if n not in front]
                front.append(random.choice(remaining))

            back_counts = [(n, count[f"back_{n}"]) for n in range(1, 13)]
            if mode == "hot":
                back_counts.sort(key=lambda x: x[1], reverse=True)
                b1, b2 = back_counts[0][0], back_counts[1][0]
            elif mode == "cold":
                back_counts.sort(key=lambda x: x[1])
                b1, b2 = back_counts[0][0], back_counts[1][0]
            else:
                back_counts.sort(key=lambda x: x[1], reverse=True)
                selected_backs = random.sample(back_counts[:4], 2)
                b1, b2 = sorted(s[0] for s in selected_backs)

            result = self._format_dlt(front, [b1, b2])
            result["metadata"] = {
                "mode": mode,
                "window": window,
                "strategy": self.name
            }
            return result
