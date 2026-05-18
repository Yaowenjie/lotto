"""🎯 预测页"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from database.db import get_ssq_history, get_dlt_history
from predictor.engine import PredictorEngine, STRATEGY_NAMES
from predictor.base import LotteryType


def history_to_list(history_rows, lottery_type):
    """将数据库行转换为预测引擎需要的列表格式"""
    result = []
    for r in reversed(list(history_rows)):  # 从旧到新
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
    st.title("🎯 预测")
    lottery_type = st.session_state.get("lottery_type", "ssq")

    # 策略选择
    strategy_key = st.selectbox(
        "选择预测策略",
        options=list(STRATEGY_NAMES.keys()),
        format_func=lambda k: STRATEGY_NAMES[k],
        index=0
    )

    engine = PredictorEngine(lottery_type)
    params_def = engine.get_strategy_params(strategy_key)

    # 参数配置
    params = {}
    cols = st.columns(min(len(params_def), 3))
    for i, pdef in enumerate(params_def):
        with cols[i % 3]:
            if pdef["type"] == "select":
                params[pdef["name"]] = st.selectbox(
                    pdef["label"], pdef["options"], index=0, key=pdef["name"]
                )
            elif pdef["type"] == "slider":
                params[pdef["name"]] = st.slider(
                    pdef["label"],
                    min_value=pdef["min"], max_value=pdef["max"],
                    value=pdef["default"], key=pdef["name"]
                )
            elif pdef["type"] == "text":
                params[pdef["name"]] = st.text_input(pdef["label"], pdef["default"], key=pdef["name"])

    # 生成数量
    n_bets = st.slider("生成数量", 1, 20, 5)

    # 预测按钮
    if st.button("🚀 生成预测", type="primary"):
        history_rows = get_ssq_history(100) if lottery_type == LotteryType.SSQ else get_dlt_history(100)
        if len(history_rows) < 10:
            st.warning("历史数据不足，请先到「数据管理」页拉取数据")
            return

        history = history_to_list(history_rows, lottery_type)

        st.markdown("---")
        st.subheader(f"预测结果 ({STRATEGY_NAMES[strategy_key]})")

        results = engine.generate_batch(strategy_key, history, count=n_bets, **params)

        for i, res in enumerate(results):
            with st.expander(f"第 {i+1} 组 — {res['display']}", expanded=(i == 0)):
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(f"**号码:** {res['display']}")
                with col2:
                    if lottery_type == LotteryType.SSQ:
                        st.markdown(f"红球: {res['red']}")
                        st.markdown(f"蓝球: {res['blue']}")
                    else:
                        st.markdown(f"前区: {res['front']}")
                        st.markdown(f"后区: {res['back']}")
                if res.get("metadata"):
                    st.markdown(f"**策略参数:** `{res['metadata']}`")

    # 策略说明
    with st.expander("📖 策略说明"):
        desc_map = {
            "hot_cold": "基于近N期号码出现频率，选高频(热号)或低频(冷号)或均衡组合",
            "odd_even": "分析历史奇偶比分布，生成最常见比例的号码组合",
            "zone": "将号码池划分为多个区间，按历史分布权重在每区选取号码",
            "sum_range": "统计历史和值分布，预测和值落点，在范围内生成号码",
            "digit_end": "保证所选号码包含多种不同尾数，符合历史尾数分布规律",
            "consecutive": "按历史连号出现频率，决定是否生成连号及连号长度",
            "ac_value": "AC值反映号码组合离散度，选取历史常见AC值范围内的组合",
            "trend": "遗漏期数越多、出现频率适中的号码综合评分更高",
        }
        for k, d in desc_map.items():
            st.markdown(f"**{STRATEGY_NAMES[k]}**: {d}")
