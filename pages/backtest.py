"""📈 回测页"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from database.db import get_ssq_history, get_dlt_history
from backtest.engine import BacktestEngine
from predictor.engine import STRATEGY_NAMES
from predictor.base import LotteryType


def history_to_list(history_rows, lottery_type):
    result = []
    for r in reversed(list(history_rows)):
        if lottery_type == LotteryType.SSQ:
            result.append({
                "expect": r["expect"],
                "date": r["date"],
                "red": [r["red_1"], r["red_2"], r["red_3"],
                        r["red_4"], r["red_5"], r["red_6"]],
                "blue": r["blue"]
            })
        else:
            result.append({
                "expect": r["expect"],
                "date": r["date"],
                "front": [r["front_1"], r["front_2"], r["front_3"],
                          r["front_4"], r["front_5"]],
                "back": [r["back_1"], r["back_2"]]
            })
    return result


def render():
    st.title("📈 回测分析")
    st.markdown("用历史数据验证各策略的预测效果")
    lottery_type = st.session_state.get("lottery_type", "ssq")

    # 回测参数
    col1, col2, col3 = st.columns(3)
    with col1:
        lookback = st.slider("参考期数 (lookback)", 10, 50, 30)
    with col2:
        predict_ahead = st.slider("回测期数", 1, 30, 10)
    with col3:
        strategy_keys = st.multiselect(
            "选择策略",
            options=list(STRATEGY_NAMES.keys()),
            default=["hot_cold", "odd_even", "zone", "sum_range"],
            format_func=lambda k: STRATEGY_NAMES[k]
        )

    if st.button("🚀 运行回测", type="primary"):
        history_rows = get_ssq_history(200) if lottery_type == LotteryType.SSQ else get_dlt_history(200)
        if len(history_rows) < lookback + predict_ahead:
            st.warning(f"历史数据不足，需要至少 {lookback + predict_ahead} 期，请先拉取数据")
            return

        history = history_to_list(history_rows, lottery_type)

        results = {}
        for key in strategy_keys:
            engine = BacktestEngine(lottery_type)
            res = engine.run(history, key, lookback=lookback,
                            predict_ahead=predict_ahead)
            results[key] = res

        # 汇总对比表
        st.markdown("---")
        st.subheader("策略对比汇总")

        summary_data = []
        for key, res in results.items():
            s = res.get("summary", {})
            if "error" in res:
                continue
            row = {
                "策略": STRATEGY_NAMES[key],
                "回测期数": s.get("total_bets", 0),
            }
            if lottery_type == LotteryType.SSQ:
                red_dist = s.get("red_hit_distribution", {})
                row["红球≥4命中次数"] = sum(red_dist.get(n, 0) for n in [4, 5, 6])
                row["蓝球命中率"] = f"{s.get('blue_hit_rate', 0)*100:.1f}%"
                row["最大红球命中"] = max(red_dist.keys()) if red_dist else 0
            else:
                front_dist = s.get("front_hit_distribution", {})
                row["前区≥3命中次数"] = sum(front_dist.get(n, 0) for n in [3, 4, 5])
                back_dist = s.get("back_hit_distribution", {})
                row["后区2全中次数"] = back_dist.get(2, 0)
            summary_data.append(row)

        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

        # 详细记录
        for key, res in results.items():
            if "error" in res:
                continue
            with st.expander(f"📋 详细记录: {STRATEGY_NAMES[key]}"):
                details = res.get("details", [])
                if details:
                    df = pd.DataFrame(details)
                    st.dataframe(df, use_container_width=True)
                s = res["summary"]
                st.markdown(f"**中奖分布:** `{s.get('rank_distribution', {})}`")
                if lottery_type == LotteryType.SSQ:
                    st.markdown(f"**红球命中分布:** `{s.get('red_hit_distribution', {})}`")
                else:
                    st.markdown(f"**前区命中分布:** `{s.get('front_hit_distribution', {})}`")

    # 策略说明
    with st.expander("📖 回测说明"):
        st.markdown("""
        **回测方法**: 滑动窗口
        - 用前 `lookback` 期数据作为特征，预测第 `lookback+1` 期
        - 逐步向前滚动，共回测 `predict_ahead` 期
        
        **中奖等级 (双色球)**:
        - 一等奖: 6+1 | 二等奖: 6+0 | 三等奖: 5+1 | 四等奖: 5+0/4+1
        - 五等奖: 4+0/3+1 | 六等奖: 3+0/2+1/1+1/0+1
        
        **中奖等级 (大乐透)**:
        - 一等奖: 5+2 | 二等奖: 5+1 | 三等奖: 5+0/4+2
        - 四等奖: 4+1/3+2 | 五等奖: 4+0/3+1/2+2 ...
        """)
