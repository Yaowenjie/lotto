"""📉 历史分析页"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from database.db import get_ssq_history, get_dlt_history
from predictor.base import LotteryType


def render():
    st.title("📉 历史数据分析")
    lottery_type = st.session_state.get("lottery_type", "ssq")

    history_rows = get_ssq_history(100) if lottery_type == LotteryType.SSQ else get_dlt_history(100)
    if len(history_rows) < 5:
        st.warning("数据不足，请先拉取数据")
        return

    # 转换为列表格式（从旧到新）
    history = []
    for r in reversed(list(history_rows)):
        if lottery_type == LotteryType.SSQ:
            history.append({
                "expect": r["expect"], "date": r["date"],
                "red": [r["red_1"], r["red_2"], r["red_3"],
                        r["red_4"], r["red_5"], r["red_6"]],
                "blue": r["blue"]
            })
        else:
            history.append({
                "expect": r["expect"], "date": r["date"],
                "front": [r["front_1"], r["front_2"], r["front_3"],
                          r["front_4"], r["front_5"]],
                "back": [r["back_1"], r["back_2"]]
            })

    tab1, tab2, tab3, tab4 = st.tabs(["🔥 冷热号排行", "📊 奇偶比", "🧮 和值分布", "🔢 尾数统计"])

    with tab1:
        st.subheader("🔥 近100期号码出现频率")
        if lottery_type == LotteryType.SSQ:
            red_count = Counter()
            for row in history:
                for n in row["red"]:
                    red_count[n] += 1
            blue_count = Counter()
            for row in history:
                blue_count[row["blue"]] += 1

            c1, c2 = st.columns(2)
            with c1:
                df_red = pd.DataFrame(red_count.most_common(),
                                      columns=["号码", "出现次数"])
                fig = px.bar(df_red, x="号码", y="出现次数",
                             title="红球出现次数")
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                df_blue = pd.DataFrame(blue_count.most_common(),
                                       columns=["号码", "出现次数"])
                fig = px.bar(df_blue, x="号码", y="出现次数",
                             title="蓝球出现次数", color="出现次数",
                             color_continuous_scale="Blues")
                st.plotly_chart(fig, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**红球冷号 (出现最少)**")
                cold = red_count.most_common()[-10:][::-1]
                st.dataframe(pd.DataFrame(cold, columns=["号码", "次数"]))
            with col2:
                st.markdown("**红球热号 (出现最多)**")
                hot = red_count.most_common(10)
                st.dataframe(pd.DataFrame(hot, columns=["号码", "次数"]))
        else:
            front_count = Counter()
            for row in history:
                for n in row["front"]:
                    front_count[n] += 1
            back_count = Counter()
            for row in history:
                for n in row["back"]:
                    back_count[n] += 1

            c1, c2 = st.columns(2)
            with c1:
                df = pd.DataFrame(front_count.most_common(),
                                  columns=["号码", "出现次数"])
                fig = px.bar(df, x="号码", y="出现次数", title="前区出现次数")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                df = pd.DataFrame(back_count.most_common(),
                                  columns=["号码", "出现次数"])
                fig = px.bar(df, x="号码", y="出现次数", title="后区出现次数")
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("📊 奇偶比分布")
        if lottery_type == LotteryType.SSQ:
            ratio_count = Counter()
            for row in history:
                odds = sum(1 for n in row["red"] if n % 2 == 1)
                ratio_count[f"{odds}:{6-odds}"] += 1
            df = pd.DataFrame(ratio_count.most_common(),
                             columns=["奇偶比", "出现次数"])
            fig = px.bar(df, x="奇偶比", y="出现次数", title="红球奇偶比分布")
            st.plotly_chart(fig, use_container_width=True)
        else:
            ratio_count = Counter()
            for row in history:
                odds = sum(1 for n in row["front"] if n % 2 == 1)
                ratio_count[f"{odds}:{5-odds}"] += 1
            df = pd.DataFrame(ratio_count.most_common(),
                             columns=["奇偶比", "出现次数"])
            fig = px.bar(df, x="奇偶比", y="出现次数", title="前区奇偶比分布")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("🧮 和值分布")
        if lottery_type == LotteryType.SSQ:
            sums = [sum(row["red"]) for row in history]
        else:
            sums = [sum(row["front"]) for row in history]

        fig = go.Figure()
        fig.add_trace(go.Histogram(x=sums, nbinsx=20, name="和值"))
        fig.update_layout(title=f"和值分布 (均值={sum(sums)/len(sums):.1f})",
                         xaxis_title="和值", yaxis_title="期数")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"**和值范围:** {min(sums)} - {max(sums)}，均值: {sum(sums)/len(sums):.1f}")

    with tab4:
        st.subheader("🔢 尾数统计")
        if lottery_type == LotteryType.SSQ:
            tails = Counter()
            for row in history:
                for n in row["red"]:
                    tails[n % 10] += 1
            df = pd.DataFrame(tails.most_common(), columns=["尾数", "出现次数"])
            fig = px.bar(df, x="尾数", y="出现次数", title="红球尾数分布")
            st.plotly_chart(fig, use_container_width=True)
        else:
            tails = Counter()
            for row in history:
                for n in row["front"]:
                    tails[n % 10] += 1
            df = pd.DataFrame(tails.most_common(), columns=["尾数", "出现次数"])
            fig = px.bar(df, x="尾数", y="出现次数", title="前区尾数分布")
            st.plotly_chart(fig, use_container_width=True)
