"""📊 数据管理页"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from database.db import (
    init_db, get_ssq_history, get_dlt_history,
    get_ssq_count, get_dlt_count, upsert_ssq, upsert_dlt
)
from fetcher.ssq_fetcher import fetch_ssq_history
from fetcher.dlt_fetcher import fetch_dlt_history


def render():
    st.title("📊 数据管理")
    st.markdown("从 17500.cn 拉取最新历史开奖数据")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("双色球 (SSQ)")
        if st.button("🔄 拉取双色球 100 期", key="fetch_ssq"):
            with st.spinner("正在拉取..."):
                try:
                    rows = fetch_ssq_history(100)
                    saved = 0
                    for r in rows:
                        reds = r["red"]
                        upsert_ssq(
                            r["expect"], r["date"],
                            ",".join(f"{n:02d}" for n in reds),
                            f"{r['blue']:02d}",
                            *reds, r["blue"]
                        )
                        saved += 1
                    st.success(f"成功保存 {saved} 期双色球数据")
                except Exception as e:
                    st.error(f"拉取失败: {e}")

        rows = get_ssq_history(20)
        if rows:
            data = []
            for r in rows:
                data.append({
                    "期号": r["expect"],
                    "日期": r["date"],
                    "红球": r["red_balls"],
                    "蓝球": r["blue_ball"]
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        st.markdown(f"共 **{get_ssq_count()}** 期")

    with col2:
        st.subheader("大乐透 (DLT)")
        if st.button("🔄 拉取大乐透 100 期", key="fetch_dlt"):
            with st.spinner("正在拉取..."):
                try:
                    rows = fetch_dlt_history(100)
                    saved = 0
                    for r in rows:
                        front = r["front"]
                        back = r["back"]
                        upsert_dlt(
                            r["expect"], r["date"],
                            ",".join(f"{n:02d}" for n in front),
                            ",".join(f"{n:02d}" for n in back),
                            *front, *back
                        )
                        saved += 1
                    st.success(f"成功保存 {saved} 期大乐透数据")
                except Exception as e:
                    st.error(f"拉取失败: {e}")

        rows = get_dlt_history(20)
        if rows:
            data = []
            for r in rows:
                data.append({
                    "期号": r["expect"],
                    "日期": r["date"],
                    "前区": r["front_balls"],
                    "后区": r["back_balls"]
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        st.markdown(f"共 **{get_dlt_count()}** 期")
