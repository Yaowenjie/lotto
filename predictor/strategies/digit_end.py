"""
策略5: 尾数策略 (DigitEndStrategy)
核心规则：
  1. 统计近30期尾数频率，选取最热的前5个尾数
  2. 每个热门尾数取对应的最热号码（而非所有对应号码）
  3. 目标：选取的6个号码来自3-5种不同尾数，且至少含2个热尾数对应号
"""
import random
from collections import Counter
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType


class DigitEndStrategy(BaseStrategy):
    """
    min_distinct: 最少不同尾数 (默认3)
    """
    name = "尾数策略"
    description = "基于历史尾数分布，优先选热尾数对应的高频号码，保证尾数多样性"

    def predict(self, history: List[Dict], min_distinct: int = 3, **kwargs) -> Dict[str, Any]:
        window = 30
        min_distinct = int(min_distinct)

        if self.lottery_type == LotteryType.SSQ:
            # ---- 1. 尾数频率统计 ----
            tail_count = Counter()
            for row in history[:window]:
                for n in row["red"]:
                    tail_count[n % 10] += 1

            hot_tails = [t for t, _ in tail_count.most_common(5)]  # Top5热尾数
            all_tails = list(range(10))

            # ---- 2. 每个尾数对应的最热号码 ----
            tail_to_hottest = {}
            for tail in hot_tails:
                nums_with_tail = [n for n in range(1, 34) if n % 10 == tail]
                cnt = Counter()
                for row in history[:window]:
                    cnt.update(n for n in row["red"] if n % 10 == tail)
                if cnt:
                    top_n = cnt.most_common(1)[0][0]
                    tail_to_hottest[tail] = top_n
                else:
                    tail_to_hottest[tail] = nums_with_tail[0] if nums_with_tail else None

            # ---- 3. 生成号码：优先选热尾数的热号 ----
            selected = []
            distinct = set()

            # 第一次：选各热尾数的最热号码（每尾数最多1个）
            for tail in hot_tails:
                if len(selected) >= 6:
                    break
                n = tail_to_hottest.get(tail)
                if n and n not in selected:
                    selected.append(n)
                    distinct.add(tail)

            # 第二次：如果尾数不足，从热尾数中再补充
            attempts = 0
            while len(selected) < 6 and attempts < 300:
                attempts += 1
                tail = random.choice(hot_tails)
                candidates = [n for n in range(1, 34)
                              if n % 10 == tail and n not in selected]
                if candidates:
                    # 每个尾数取候选中最热的
                    cnt = Counter()
                    for row in history[:window]:
                        cnt.update(n for n in row["red"] if n % 10 == tail)
                    cnt_sorted = sorted(cnt.items(), key=lambda x: x[1], reverse=True)
                    for n, _ in cnt_sorted:
                        if n not in selected:
                            selected.append(n)
                            distinct.add(tail)
                            break

            # 第三次：补足6个（允许冷尾数）
            while len(selected) < 6:
                tail = random.choice(all_tails)
                candidates = [n for n in range(1, 34)
                              if n % 10 == tail and n not in selected]
                if candidates:
                    n = random.choice(candidates)
                    selected.append(n)
                    distinct.add(tail)

            selected = sorted(set(selected))[:6]

            blue = random.randint(1, 16)
            result = self._format_ssq(selected, blue)
            result["metadata"] = {
                "distinct_tails": len(set(n % 10 for n in selected)),
                "hot_tails": hot_tails,
                "tail_distribution": dict(tail_count.most_common(5)),
                "strategy": self.name
            }
            return result

        else:  # DLT
            tail_count = Counter()
            for row in history[:window]:
                for n in row["front"]:
                    tail_count[n % 10] += 1

            hot_tails = [t for t, _ in tail_count.most_common(5)]
            all_tails = list(range(10))

            front = []
            distinct = set()

            # 优先选热尾数的热号
            for tail in hot_tails:
                if len(front) >= 5:
                    break
                nums_with_tail = [n for n in range(1, 36) if n % 10 == tail]
                cnt = Counter()
                for row in history[:window]:
                    cnt.update(n for n in row["front"] if n % 10 == tail)
                if cnt:
                    top_n = cnt.most_common(1)[0][0]
                    if top_n not in front:
                        front.append(top_n)
                        distinct.add(tail)

            while len(front) < 5:
                tail = random.choice(hot_tails if random.random() < 0.7 else all_tails)
                candidates = [n for n in range(1, 36)
                              if n % 10 == tail and n not in front]
                if candidates:
                    front.append(random.choice(candidates))
                    distinct.add(tail)

            back_pool = list(range(1, 13))
            back = random.sample(back_pool, 2)

            result = self._format_dlt(front, back)
            result["metadata"] = {
                "distinct_tails": len(distinct),
                "strategy": self.name
            }
            return result