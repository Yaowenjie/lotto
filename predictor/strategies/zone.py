"""
策略3: 区间分布策略 (ZoneStrategy)
核心规则：
  1. 号码分3区(1-11/12-22/23-33)，按历史各区出现频率分配名额
  2. 位置频率：每位置选取历史最热Top3候选，限制奇偶比例
  3. 每区号码不超3个，避免某区过度集中
"""
import random
from collections import Counter
from typing import List, Dict, Any
from predictor.base import BaseStrategy, LotteryType


class ZoneStrategy(BaseStrategy):
    """
    zones: 区间数量 (默认3)
    """
    name = "区间分布策略"
    description = "将号码划分为多个区间，按历史分布决定每区选号数量，加入位置热号约束"

    def predict(self, history: List[Dict], zones: int = 3,
                min_per_zone: int = 1, **kwargs) -> Dict[str, Any]:
        zones = int(zones)
        window = 30

        if self.lottery_type == LotteryType.SSQ:
            # ---- 1. 位置热度统计 (每位置Top5候选) ----
            pos_candidates = []
            for pos in range(6):
                cnt = Counter(row["red"][pos] for row in history[:window])
                top5 = [n for n, _ in cnt.most_common(5)]
                pos_candidates.append(top5 if top5 else list(range(1, 34)))

            # ---- 2. 区间定义 ----
            red_range = list(range(1, 34))
            zone_size = 33 // zones
            zone_ranges = []
            for i in range(zones - 1):
                zone_ranges.append(red_range[i * zone_size:(i + 1) * zone_size])
            zone_ranges.append(red_range[(zones - 1) * zone_size:])

            # ---- 3. 历史各区出现频率 ----
            zone_counts = [0] * zones
            for row in history[:window]:
                for n in row["red"]:
                    for zi, zr in enumerate(zone_ranges):
                        if n in zr:
                            zone_counts[zi] += 1
                            break

            # ---- 4. 按权重分配名额（每区最多3个）----
            total = sum(zone_counts) + 1
            zone_weights = [c / total for c in zone_counts]

            selected = []
            zone_used = [0] * zones
            for _ in range(100):  # 最多尝试100次找合法解
                if len(selected) >= 6:
                    break
                zi = random.choices(range(zones), weights=zone_weights)[0]
                if zone_used[zi] >= 3:
                    zi = min(range(zones), key=lambda z: zone_used[z])
                pool = [n for n in zone_ranges[zi] if n not in selected]
                if not pool:
                    pool = [n for n in range(1, 34) if n not in selected]
                selected.append(random.choice(pool))
                zone_used[zi] += 1

            # ---- 5. 位置热号替换：如果某位不在热号候选中，替换 ----
            final = []
            for pos in range(6):
                pos_pool = pos_candidates[pos]
                # 优先用已有选号中属于位置热号的
                candidates = [n for n in selected if n in pos_pool]
                if candidates:
                    chosen = random.choice(candidates)
                    selected.remove(chosen)
                    final.append(chosen)
                else:
                    chosen = random.choice(pos_pool)
                    # 避免重复
                    while chosen in final and len(pos_pool) > 1:
                        chosen = random.choice(pos_pool)
                    final.append(chosen)

            # ---- 6. 奇偶比例约束 ----
            for attempt in range(200):
                odds = sum(1 for n in final if n % 2 == 1)
                if 1 <= odds <= 5:
                    break
                # 替换一个奇偶不合适的号
                idx = random.randint(0, 5)
                pos_pool = pos_candidates[idx]
                new_n = random.choice(pos_pool)
                final[idx] = new_n

            final = sorted(set(final))
            while len(final) < 6:
                for pos in range(6):
                    if len(final) >= 6:
                        break
                    pos_pool = pos_candidates[pos]
                    candidates = [n for n in pos_pool if n not in final]
                    if candidates:
                        final.append(random.choice(candidates))
            final = sorted(final)[:6]

            blue = random.randint(1, 16)
            result = self._format_ssq(final, blue)
            result["metadata"] = {
                "zones": zones,
                "zone_counts": zone_counts,
                "zone_ranges": [f"{min(zr)}-{max(zr)}" for zr in zone_ranges],
                "strategy": self.name
            }
            return result

        else:  # DLT
            front_range = list(range(1, 36))
            fzone_size = 35 // zones
            fzone_ranges = []
            for i in range(zones - 1):
                fzone_ranges.append(front_range[i * fzone_size:(i + 1) * fzone_size])
            fzone_ranges.append(front_range[(zones - 1) * fzone_size:])

            zone_counts = [0] * zones
            for row in history[:window]:
                for n in row["front"]:
                    for zi, zr in enumerate(fzone_ranges):
                        if n in zr:
                            zone_counts[zi] += 1
                            break

            total = sum(zone_counts) + 1
            zone_weights = [c / total for c in zone_counts]

            front = []
            zone_used = [0] * zones
            for _ in range(100):
                if len(front) >= 5:
                    break
                zi = random.choices(range(zones), weights=zone_weights)[0]
                if zone_used[zi] >= 2:
                    zi = min(range(zones), key=lambda z: zone_used[z])
                pool = [n for n in fzone_ranges[zi] if n not in front]
                if not pool:
                    pool = [n for n in range(1, 36) if n not in front]
                front.append(random.choice(pool))
                zone_used[zi] += 1

            front = sorted(set(front))[:5]
            while len(front) < 5:
                remaining = [n for n in range(1, 36) if n not in front]
                front.append(random.choice(remaining))

            back_pool = list(range(1, 13))
            back = random.sample(back_pool, 2)

            result = self._format_dlt(front, back)
            result["metadata"] = {
                "zones": zones,
                "strategy": self.name
            }
            return result