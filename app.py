"""
彩票预测分析应用 — 全新深色卡片风格 UI
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
from database.db import init_db, get_ssq_history, get_dlt_history, \
    get_ssq_count, get_dlt_count, upsert_ssq, upsert_dlt
from fetcher.ssq_fetcher import fetch_ssq_history
from fetcher.dlt_fetcher import fetch_dlt_history
from predictor.engine import PredictorEngine, STRATEGY_NAMES
from backtest.engine import BacktestEngine
from predictor.base import LotteryType
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

init_db()

# ─────────────────────────────────────────────────────────────
# 主题配置
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="彩票预测分析",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 深色主题全局样式
st.markdown("""
<style>
    /* 全局字体与背景 */
    .stApp { background: #0d1117; color: #e6edf3; }

    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: #161b22 !important;
        border-right: 1px solid #30363d;
    }

    /* Tab 样式 */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #161b22; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: #8b949e; border-radius: 6px;
        font-weight: 600; padding: 8px 20px; border: none;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover { background: #21262d; color: #e6edf3; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #238636 !important; color: #ffffff !important;
    }

    /* 主标题 */
    .main-title { font-size: 2rem; font-weight: 700; color: #e6edf3;
                   margin-bottom: 0.2rem; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #8b949e;
                     text-transform: uppercase; letter-spacing: 0.05em; margin-top: 1.5rem; }

    /* 卡片 */
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px;
            padding: 1.2rem; margin-bottom: 1rem; }
    .card-title { font-size: 1rem; font-weight: 600; color: #e6edf3; margin-bottom: 0.6rem; }
    .card-sub { font-size: 0.85rem; color: #8b949e; }

    /* 统计数字 */
    .stat-big { font-size: 2rem; font-weight: 700; color: #58a6ff; }
    .stat-label { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; }

    /* 预测号码展示 */
    .pred-row { display: flex; align-items: center; gap: 8px; margin: 4px 0; }

    /* 按钮 */
    .stButton > button { border-radius: 8px; font-weight: 600;
                          border: 1px solid #30363d; transition: all 0.2s; }
    .stButton > button:hover { border-color: #58a6ff; }

    /* Dataframe */
    [data-testid="stDataFrame"] table { color: #e6edf3 !important; }
    [data-testid="stDataFrame"] thead th { background: #21262d !important; color: #8b949e !important; }

    /* Expander */
    .streamlit-expanderHeader { background: #161b22; border-radius: 8px;
                                  color: #e6edf3; border: 1px solid #30363d; }

    /* Metric */
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d;
                                border-radius: 8px; padding: 12px; }

    /* 进度条 */
    .stProgress > div > div { background: #238636; }

    /* 成功/错误/警告 */
    .stAlert { border-radius: 8px; }

    /* 侧边栏文字 */
    [data-testid="stSidebar"] .stMarkdown { color: #e6edf3; }

    /* 隐藏右上角 Streamlit 标记 */
    /* 隐藏 Streamlit 侧边导航及顶部菜单 */
    [data-testid="stSidebarNav"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Plotly 深色主题 */
    .js-plotly-plot .plotly { background: #161b22 !important; }

    /* 预测结果表格 */
    .result-table { background: #161b22; border-radius: 8px; padding: 16px;
                     border: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────
def rows_to_list(rows, ltype):
    result = []
    # DB 查询已是 ORDER BY expect DESC（最新在前），直接遍历即可
    for r in rows:
        if ltype == LotteryType.SSQ:
            result.append({
                "expect": r["expect"], "date": r["date"],
                "red": [r["red_1"], r["red_2"], r["red_3"],
                        r["red_4"], r["red_5"], r["red_6"]],
                "blue": r["blue"]
            })
        else:
            result.append({
                "expect": r["expect"], "date": r["date"],
                "front": [r["front_1"], r["front_2"], r["front_3"],
                          r["front_4"], r["front_5"]],
                "back": [r["back_1"], r["back_2"]]
            })
    return result


def render_balls_ssq(reds, blue, size=36):
    """渲染双色球红球+蓝球 HTML"""
    fs = max(10, int(size * 0.32))
    r_html = "".join(
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#f85149;color:white;font-weight:700;font-size:{fs}px;margin:2px;">{n:02d}</span>'
        for n in reds
    )
    b_html = (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#1f6feb;color:white;font-weight:700;font-size:{fs}px;margin:2px;">{blue:02d}</span>'
    )
    return f'<div style="display:flex;align-items:center;gap:4px;">{r_html}&nbsp;{b_html}</div>'


def render_balls_dlt(front, back, size=36):
    """渲染大乐透前区+后区 HTML"""
    fs = max(10, int(size * 0.32))
    f_html = "".join(
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#a371f7;color:white;font-weight:700;font-size:{fs}px;margin:2px;">{n:02d}</span>'
        for n in front
    )
    b_html = "".join(
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#3fb950;color:white;font-weight:700;font-size:{fs}px;margin:2px;">{n:02d}</span>'
        for n in back
    )
    plus_fs = max(10, int(size * 0.5))
    return f'<div style="display:flex;align-items:center;gap:8px;">{f_html}<span style="color:#8b949e;font-size:{plus_fs}px;">+</span>{b_html}</div>'


def plotly_dark(fig):
    """应用深色主题到 Plotly 图表（手动配置，避免 plotly_dark 模板字体过大）"""
    fig.update_layout(
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#e6edf3", size=13),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor="#30363d", color="#8b949e", tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="#30363d", color="#8b949e", tickfont=dict(size=11))
    return fig


def render_result_table(results, lt):
    """将预测结果列表渲染为 DataFrame（用于 st.dataframe）"""
    rows = []
    for i, res in enumerate(results):
        if lt == LotteryType.SSQ:
            rows.append({
                "组别": i + 1,
                "红球": " ".join(f"{n:02d}" for n in res["red"]),
                "蓝球": f"{res['blue']:02d}",
                "红球列表": ", ".join(f"{n:02d}" for n in res["red"]),
                "蓝球": f"{res['blue']:02d}",
            })
        else:
            rows.append({
                "组别": i + 1,
                "前区": " ".join(f"{n:02d}" for n in res["front"]),
                "后区": " ".join(f"{n:02d}" for n in res["back"]),
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# 侧边栏
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎯 彩票预测")
    st.markdown("---")

    ssq_cnt = get_ssq_count()
    dlt_cnt = get_dlt_count()

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("双色球", f"{ssq_cnt}期")
    with col_b:
        st.metric("大乐透", f"{dlt_cnt}期")

    st.markdown("---")

    lottery_label = st.radio(
        "**选择彩种**",
        ["🔴 双色球 (SSQ)", "🟣 大乐透 (DLT)"],
        index=0,
        label_visibility="visible"
    )
    st.session_state["lottery_type"] = "ssq" if "SSQ" in lottery_label else "dlt"

    st.markdown("---")
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")

# ─────────────────────────────────────────────────────────────
# 主区域 Tab 导航
# ─────────────────────────────────────────────────────────────
TAB_NAMES = ["📊 数据管理", "🎯 预测", "📈 回测", "📉 历史分析"]
tabs = st.tabs(TAB_NAMES)

lt = st.session_state.get("lottery_type", "ssq")

# ═══════════════════════════════════════════════════════════════
# Tab 0: 数据管理
# ═══════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown('<p class="main-title">📊 数据管理</p>', unsafe_allow_html=True)
    st.markdown("从 **17500.cn** 拉取最新历史开奖数据")

    # 拉取按钮
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🔴 双色球")
        if st.button("🔄 拉取/更新 100 期", key="btn_fetch_ssq", use_container_width=True, type="primary"):
            with st.spinner("正在拉取双色球数据..."):
                try:
                    rows = fetch_ssq_history(100)
                    saved = 0
                    for r in rows:
                        upsert_ssq(
                            r["expect"], r["date"],
                            ",".join(f"{n:02d}" for n in r["red"]),
                            f"{r['blue']:02d}",
                            *r["red"], r["blue"]
                        )
                        saved += 1
                    st.session_state["ssq_fetch_msg"] = f"✅ 成功保存 {saved} 期 (最新: {rows[0]['expect']})"
                except Exception as e:
                    st.session_state["ssq_fetch_msg"] = f"❌ 拉取失败: {e}"
            if msg := st.session_state.get("ssq_fetch_msg"):
                if "✅" in msg:
                    st.success(msg)
                else:
                    st.error(msg)
                st.session_state.pop("ssq_fetch_msg", None)
                st.rerun()

    with c2:
        st.markdown("#### 🟣 大乐透")
        if st.button("🔄 拉取/更新 100 期", key="btn_fetch_dlt", use_container_width=True, type="primary"):
            with st.spinner("正在拉取大乐透数据..."):
                try:
                    rows = fetch_dlt_history(100)
                    saved = 0
                    for r in rows:
                        upsert_dlt(
                            r["expect"], r["date"],
                            ",".join(f"{n:02d}" for n in r["front"]),
                            ",".join(f"{n:02d}" for n in r["back"]),
                            *r["front"], *r["back"]
                        )
                        saved += 1
                    st.session_state["dlt_fetch_msg"] = f"✅ 成功保存 {saved} 期 (最新: {rows[0]['expect']})"
                except Exception as e:
                    st.session_state["dlt_fetch_msg"] = f"❌ 拉取失败: {e}"
            if msg := st.session_state.get("dlt_fetch_msg"):
                if "✅" in msg:
                    st.success(msg)
                else:
                    st.error(msg)
                st.session_state.pop("dlt_fetch_msg", None)
                st.rerun()

    st.markdown("---")

    # 最新开奖展示
    st.markdown("#### 🏆 最新开奖")

    col_latest_ssq, col_latest_dlt = st.columns(2)

    rows_ssq = get_ssq_history(5)
    rows_dlt = get_dlt_history(5)

    with col_latest_ssq:
        st.markdown("**🔴 双色球**")
        if rows_ssq:
            for r in list(rows_ssq)[:3]:
                reds = [r["red_1"], r["red_2"], r["red_3"], r["red_4"], r["red_5"], r["red_6"]]
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'>"
                    f"<span style='color:#8b949e;font-size:12px;min-width:80px;'>{r['expect']}</span>"
                    f"{render_balls_ssq(reds, r['blue'], 30)}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("暂无数据，请先拉取")

    with col_latest_dlt:
        st.markdown("**🟣 大乐透**")
        if rows_dlt:
            for r in list(rows_dlt)[:3]:
                front = [r["front_1"], r["front_2"], r["front_3"], r["front_4"], r["front_5"]]
                back = [r["back_1"], r["back_2"]]
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0;'>"
                    f"<span style='color:#8b949e;font-size:12px;min-width:80px;'>{r['expect']}</span>"
                    f"{render_balls_dlt(front, back, 30)}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("暂无数据，请先拉取")

    st.markdown("---")

    # 历史数据表格
    tc1, tc2 = st.columns(2)
    with tc1:
        st.markdown("#### 🔴 双色球历史")
        rows = get_ssq_history(30)
        if rows:
            data = [{"期号": r["expect"], "日期": r["date"],
                     "红球": r["red_balls"], "蓝球": r["blue_ball"]} for r in rows]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True,
                         height=400)
        st.caption(f"共 {get_ssq_count()} 期")

    with tc2:
        st.markdown("#### 🟣 大乐透历史")
        rows = get_dlt_history(30)
        if rows:
            data = [{"期号": r["expect"], "日期": r["date"],
                     "前区": r["front_balls"], "后区": r["back_balls"]} for r in rows]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True,
                         height=400)
        st.caption(f"共 {get_dlt_count()} 期")


# ═══════════════════════════════════════════════════════════════
# Tab 1: 预测
# ═══════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<p class="main-title">🎯 预测</p>', unsafe_allow_html=True)
    st.markdown("基于历史数据规律生成预测号码")

    # 策略 + 参数 同一行
    engine = PredictorEngine(lt)

    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])

    with ctrl_col1:
        strategy_key = st.selectbox(
            "**策略**",
            options=list(STRATEGY_NAMES.keys()),
            format_func=lambda k: STRATEGY_NAMES[k], index=0,
            key="sel_strategy",
        )

    with ctrl_col2:
        params_def = engine.get_strategy_params(strategy_key)
        params = {}
        # 单行展示所有参数
        param_cols = st.columns(len(params_def)) if params_def else [st]
        for i, pdef in enumerate(params_def):
            with param_cols[i]:
                if pdef["type"] == "select":
                    params[pdef["name"]] = st.selectbox(
                        pdef["label"], pdef["options"], index=0,
                        key=f"p_{strategy_key}_{pdef['name']}"
                    )
                elif pdef["type"] == "slider":
                    params[pdef["name"]] = st.slider(
                        pdef["label"], min_value=pdef["min"], max_value=pdef["max"],
                        value=pdef["default"], key=f"p_{strategy_key}_{pdef['name']}"
                    )
                elif pdef["type"] == "text":
                    params[pdef["name"]] = st.text_input(
                        pdef["label"], pdef["default"],
                        key=f"p_{strategy_key}_{pdef['name']}"
                    )

    with ctrl_col3:
        n_bets = st.selectbox("**组数**", options=list(range(1, 21)), index=4, key="sel_n_bets")
        st.markdown("")  # spacer

    st.markdown("")

    if st.button("🚀 生成预测", key="btn_generate", type="primary", use_container_width=True):
        rows = get_ssq_history(100) if lt == "ssq" else get_dlt_history(100)
        if len(rows) < 10:
            st.warning("⚠️ 历史数据不足，请先到「数据管理」拉取数据")
        else:
            history = rows_to_list(rows, lt)
            results = engine.generate_batch(strategy_key, history, count=n_bets, **params)

            st.markdown("---")

            # 预测结果 — 球号可视化
            st.markdown(f"#### 📋 预测结果 ({n_bets} 组)")

            # 最新一期对照
            latest = history[0]
            if lt == LotteryType.SSQ:
                st.markdown(f"**最近一期实际开奖** — {latest['expect']}  {render_balls_ssq(latest['red'], latest['blue'], 32)}",
                            unsafe_allow_html=True)
            else:
                st.markdown(f"**最近一期实际开奖** — {latest['expect']}  {render_balls_dlt(latest['front'], latest['back'], 32)}",
                            unsafe_allow_html=True)

            st.markdown("")

            # 分两列展示预测结果
            half = (len(results) + 1) // 2
            left, right = st.columns(2)

            for idx, res in enumerate(results):
                col = left if idx < half else right
                with col:
                    num_str = res["display"]
                    if lt == LotteryType.SSQ:
                        red_nums = res["red"]
                        blue_num = res["blue"]
                        ball_html = render_balls_ssq(red_nums, blue_num, 38)
                        badge = f"第 {idx+1} 组"
                    else:
                        front_nums = res["front"]
                        back_nums = res["back"]
                        ball_html = render_balls_dlt(front_nums, back_nums, 38)
                        badge = f"第 {idx+1} 组"

                    with st.container():
                        st.markdown(
                            f"<div class='card' style='padding:0.8rem;'>"
                            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                            f"<span style='color:#8b949e;font-size:13px;'>{badge}</span>"
                            f"<span style='font-size:13px;color:#8b949e;font-family:monospace;'>{num_str}</span>"
                            f"</div>"
                            f"<div style='margin-top:8px;'>{ball_html}</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        if res.get("metadata"):
                            with st.expander("策略详情"):
                                st.json(res["metadata"])

            st.markdown("")

            # 策略说明
            with st.expander("📖 策略说明"):
                desc_map = {
                    "hot_cold": "基于近N期号码出现频率，选高频(热号)或低频(冷号)或均衡组合",
                    "odd_even": "分析历史奇偶比分布，生成最常见比例的号码组合",
                    "zone": "将号码池划分为多个区间，按历史分布权重在每区选取号码",
                    "sum_range": "统计历史和值分布，预测和值落点，在范围内生成号码",
                    "digit_end": "保证所选号码包含多种不同尾数，符合历史尾数分布规律",
                    "consecutive": "每期约80%存在1-2个重复号；本策略从上期号码中选取重复号作为核心",
                    "ac_value": "去掉AC值硬过滤，改为位置热号+和值+奇偶比+尾数分散度四重约束",
                    "trend": "多因子评分模型（位置50%+频率30%+遗漏20%），遗漏越大评分越高",
                }
                for k, d in desc_map.items():
                    st.markdown(f"**{STRATEGY_NAMES[k]}**: {d}")


# ═══════════════════════════════════════════════════════════════
# Tab 2: 回测
# ═══════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<p class="main-title">📈 回测分析</p>', unsafe_allow_html=True)
    st.markdown("用历史数据验证各策略的预测效果，滑动窗口模拟真实预测")

    # 参数行
    p_col1, p_col2, p_col3 = st.columns([1, 1, 2])
    with p_col1:
        lookback = st.slider("参考期数", 10, 50, 30, key="slider_lookback",
                             help="用多少期历史数据做预测依据")
    with p_col2:
        predict_ahead = st.slider("回测期数", 1, 30, 10, key="slider_predict_ahead",
                                  help="向前预测多少期")

    st.markdown("")

    default_strategies = ["hot_cold", "odd_even", "zone", "sum_range", "trend"]
    strategy_keys = st.multiselect(
        "**选择策略 (多选)**",
        options=list(STRATEGY_NAMES.keys()),
        default=default_strategies,
        format_func=lambda k: STRATEGY_NAMES[k],
        key="ms_strategy_keys",
    )

    # 策略参数（仅展示第一个选中策略）
    bt_params = {}
    if strategy_keys:
        first_key = strategy_keys[0]
        engine_bt = BacktestEngine(lt)
        param_defs = engine_bt.engine.get_strategy_params(first_key)
        if param_defs:
            st.markdown("**策略参数**")
            param_cols = st.columns(len(param_defs))
            for i, pd_ in enumerate(param_defs):
                with param_cols[i]:
                    if pd_["type"] == "select":
                        bt_params[pd_["name"]] = st.selectbox(
                            pd_["label"], pd_["options"], index=0,
                            key=f"bt_p_{first_key}_{pd_['name']}"
                        )
                    elif pd_["type"] == "slider":
                        bt_params[pd_["name"]] = st.slider(
                            pd_["label"], min_value=pd_["min"], max_value=pd_["max"],
                            value=pd_["default"],
                            key=f"bt_p_{first_key}_{pd_['name']}"
                        )
                    elif pd_["type"] == "text":
                        bt_params[pd_["name"]] = st.text_input(
                            pd_["label"], pd_["default"],
                            key=f"bt_p_{first_key}_{pd_['name']}"
                        )

    st.markdown("")

    if st.button("🚀 运行回测", key="btn_backtest", type="primary", use_container_width=True):
        rows = get_ssq_history(200) if lt == "ssq" else get_dlt_history(200)
        if len(rows) < lookback + predict_ahead:
            st.warning(f"⚠️ 数据不足，需要至少 {lookback + predict_ahead} 期，请先拉取数据")
        else:
            history = rows_to_list(rows, lt)
            summary_rows = []
            detail_data = {}

            for key in strategy_keys:
                engine_bt = BacktestEngine(lt)
                res = engine_bt.run(history, key, lookback=lookback,
                                     predict_ahead=predict_ahead, params=bt_params)
                if "error" in res:
                    continue
                s = res["summary"]

                if lt == LotteryType.SSQ:
                    rd = s.get("red_hit_distribution", {})
                    wins_3plus = sum(rd.get(n, 0) for n in [3, 4, 5, 6])
                    win_rate = wins_3plus / s["total_bets"] if s["total_bets"] > 0 else 0
                    summary_rows.append({
                        "策略": STRATEGY_NAMES[key],
                        "回测期数": s["total_bets"],
                        "≥3红中奖": wins_3plus,
                        "中奖率": f"{win_rate*100:.1f}%",
                        "4红+": sum(rd.get(n, 0) for n in [4, 5, 6]),
                        "最大红球命中": max(rd.keys()) if rd else 0,
                    })
                else:
                    fd = s.get("front_hit_distribution", {})
                    wins_3plus = sum(fd.get(n, 0) for n in [3, 4, 5])
                    win_rate = wins_3plus / s["total_bets"] if s["total_bets"] > 0 else 0
                    summary_rows.append({
                        "策略": STRATEGY_NAMES[key],
                        "回测期数": s["total_bets"],
                        "≥3前区中奖": wins_3plus,
                        "中奖率": f"{win_rate*100:.1f}%",
                        "最大前区命中": max(fd.keys()) if fd else 0,
                    })

                detail_data[key] = res

            if summary_rows:
                df_summary = pd.DataFrame(summary_rows)

                # 可视化柱状图
                st.markdown("#### 📊 中奖率对比")
                if lt == LotteryType.SSQ:
                    fig = px.bar(
                        df_summary,
                        x="策略", y="≥3红中奖",
                        color="中奖率",
                        color_continuous_scale="RdYlGn",
                        range_color=[0, 0.5],
                        text="中奖率",
                    )
                else:
                    fig = px.bar(
                        df_summary,
                        x="策略", y="≥3前区中奖",
                        color="中奖率",
                        color_continuous_scale="RdYlGn",
                        range_color=[0, 0.5],
                        text="中奖率",
                    )
                fig = plotly_dark(fig)
                fig.update_layout(xaxis_tickangle=-20, showlegend=False,
                                  title=dict(text="各策略中奖次数对比", font=dict(size=14)))
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig, use_container_width=True)

                # 汇总表格
                st.markdown("#### 📋 汇总数据")
                st.dataframe(df_summary, use_container_width=True, hide_index=True,
                             height=300)

                # 详细记录
                st.markdown("#### 📋 详细预测记录")
                for key in strategy_keys:
                    res = detail_data[key]
                    details = res.get("details", [])
                    if not details:
                        continue

                    with st.expander(f"**{STRATEGY_NAMES[key]}** 详细记录"):
                        # 命中分布
                        s = res["summary"]
                        if lt == LotteryType.SSQ:
                            rd = s.get("red_hit_distribution", {})
                            hits = ["0红", "1红", "2红", "3红", "4红", "5红", "6红"]
                            vals = [rd.get(i, 0) for i in range(7)]
                            fig2 = go.Figure(go.Bar(
                                x=hits, y=vals,
                                marker_color=["#f85149" if v == 0 else "#238636" if v >= 3 else "#8b949e"
                                              for v in vals]
                            ))
                            fig2 = plotly_dark(fig2)
                            fig2.update_layout(title=dict(text="红球命中分布", font=dict(size=12)),
                                              xaxis_title="红球命中数", yaxis_title="期数",
                                              height=250)
                            st.plotly_chart(fig2, use_container_width=True)
                        else:
                            fd = s.get("front_hit_distribution", {})
                            hits = [f"{i}前" for i in range(6)]
                            vals = [fd.get(i, 0) for i in range(6)]
                            fig2 = go.Figure(go.Bar(x=hits, y=vals, marker_color="#a371f7"))
                            fig2 = plotly_dark(fig2)
                            fig2.update_layout(title=dict(text="前区命中分布", font=dict(size=12)),
                                              xaxis_title="前区命中数", yaxis_title="期数",
                                              height=250)
                            st.plotly_chart(fig2, use_container_width=True)

                        # 明细表格
                        det_df = pd.DataFrame(details)
                        # 增加颜色标记红球命中数列
                        st.dataframe(det_df, use_container_width=True, hide_index=True, height=350)

    # 回测说明
    with st.expander("📖 回测说明"):
        st.markdown("""
        **方法**: 滑动窗口 — 用前 `lookback` 期预测第 `lookback+1` 期，逐步向前滚动。

        **中奖标准**: ≥3红球命中（双色球）或 ≥3前区命中（大乐透）为中奖
            
        **双色球奖项等级**:
        - 一等奖=6+1 | 二等奖=6+0 | 三等奖=5+1 | 四等奖=5+0/4+1 | 五等奖=4+0/3+1 | 六等奖=2+1/1+1/0+1

        **大乐透奖项等级**:
        - 一等奖=5+2 | 二等奖=5+1 | 三等奖=5+0/4+2 | 四等奖=4+1/3+2 | 五等奖=4+0/3+1/2+2 | 六等奖=3+0/1+2/2+1/0+2 | 七等奖=2+0/1+1/0+1 | 八等奖=1+0/0+0
        """)


# ═══════════════════════════════════════════════════════════════
# Tab 3: 历史分析
# ═══════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown('<p class="main-title">📉 历史数据分析</p>', unsafe_allow_html=True)
    rows = get_ssq_history(100) if lt == "ssq" else get_dlt_history(100)

    if len(rows) < 5:
        st.warning("⚠️ 数据不足，请先拉取数据")
    else:
        history = rows_to_list(rows, lt)

        # 顶部 KPI 指标卡
        if lt == LotteryType.SSQ:
            red_count = Counter()
            blue_count = Counter()
            for row in history:
                for n in row["red"]:
                    red_count[n] += 1
                blue_count[row["blue"]] += 1
            hot_red = red_count.most_common(1)[0]
            cold_red = red_count.most_common()[-1]
            hot_blue = blue_count.most_common(1)[0]
            avg_sum = sum(sum(row["red"]) for row in history) / len(history)
            odds_dist = Counter(
                f"{sum(1 for n in row['red'] if n%2==1)}:{6-sum(1 for n in row['red'] if n%2==1)}"
                for row in history
            )
            hot_ratio = odds_dist.most_common(1)[0]
        else:
            front_count = Counter()
            back_count = Counter()
            for row in history:
                for n in row["front"]:
                    front_count[n] += 1
                for n in row["back"]:
                    back_count[n] += 1
            hot_front = front_count.most_common(1)[0]
            cold_front = front_count.most_common()[-1]
            avg_sum = sum(sum(row["front"]) for row in history) / len(history)
            odds_dist = Counter(
                f"{sum(1 for n in row['front'] if n%2==1)}:{5-sum(1 for n in row['front'] if n%2==1)}"
                for row in history
            )
            hot_ratio = odds_dist.most_common(1)[0]

        # KPI 行
        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            if lt == LotteryType.SSQ:
                st.metric("🔥 最热红球", f"{hot_red[0]:02d}", f"{hot_red[1]}次")
            else:
                st.metric("🔥 最热前区", f"{hot_front[0]:02d}", f"{hot_front[1]}次")
        with kpi_cols[1]:
            if lt == LotteryType.SSQ:
                st.metric("❄️ 最冷红球", f"{cold_red[0]:02d}", f"{cold_red[1]}次")
            else:
                st.metric("❄️ 最冷前区", f"{cold_front[0]:02d}", f"{cold_front[1]}次")
        with kpi_cols[2]:
            st.metric("📊 红球均和值", f"{avg_sum:.0f}")
        with kpi_cols[3]:
            st.metric("📈 最常见奇偶", hot_ratio[0], f"{hot_ratio[1]}次")

        st.markdown("")

        # 子 Tab
        sub_tab_labels = ["🔥 冷热号", "📊 奇偶比", "🧮 和值分布", "🔢 尾数统计", "🔗 重复号规律"]
        sub_tabs = st.tabs(sub_tab_labels)

        with sub_tabs[0]:
            st.markdown("#### 🔥 近 100 期号码出现频率")
            if lt == LotteryType.SSQ:
                rc, bc = st.columns(2)
                with rc:
                    df = pd.DataFrame(red_count.most_common(), columns=["号码", "次数"])
                    fig = px.bar(df, x="号码", y="次数", title="红球出现次数",
                                 color="次数", color_continuous_scale="Reds")
                    fig = plotly_dark(fig)
                    fig.update_traces(marker_line=dict(width=0))
                    st.plotly_chart(fig, use_container_width=True)

                    # 热冷号表格
                    hc_col1, hc_col2 = st.columns(2)
                    with hc_col1:
                        st.markdown("**🔥 热号 TOP10**")
                        hot_df = pd.DataFrame(red_count.most_common(10), columns=["号码", "次数"])
                        st.dataframe(hot_df, hide_index=True, height=260)
                    with hc_col2:
                        st.markdown("**❄️ 冷号 TOP10**")
                        cold_df = pd.DataFrame(red_count.most_common()[-10:], columns=["号码", "次数"])
                        st.dataframe(cold_df, hide_index=True, height=260)

                with bc:
                    df_b = pd.DataFrame(blue_count.most_common(), columns=["号码", "次数"])
                    fig_b = px.bar(df_b, x="号码", y="次数", title="蓝球出现次数",
                                   color="次数", color_continuous_scale="Blues")
                    fig_b = plotly_dark(fig_b)
                    fig_b.update_traces(marker_line=dict(width=0))
                    st.plotly_chart(fig_b, use_container_width=True)
            else:
                fc, bc_ = st.columns(2)
                with fc:
                    df = pd.DataFrame(front_count.most_common(), columns=["号码", "次数"])
                    fig = px.bar(df, x="号码", y="次数", title="前区出现次数",
                                 color="次数", color_continuous_scale="Purples")
                    fig = plotly_dark(fig)
                    fig.update_traces(marker_line=dict(width=0))
                    st.plotly_chart(fig, use_container_width=True)

                    hc_col1, hc_col2 = st.columns(2)
                    with hc_col1:
                        st.markdown("**🔥 热号 TOP10**")
                        st.dataframe(pd.DataFrame(front_count.most_common(10), columns=["号码", "次数"]), hide_index=True, height=260)
                    with hc_col2:
                        st.markdown("**❄️ 冷号 TOP10**")
                        st.dataframe(pd.DataFrame(front_count.most_common()[-10:], columns=["号码", "次数"]), hide_index=True, height=260)

                with bc_:
                    df_b = pd.DataFrame(back_count.most_common(), columns=["号码", "次数"])
                    fig_b = px.bar(df_b, x="号码", y="次数", title="后区出现次数",
                                   color="次数", color_continuous_scale="Greens")
                    fig_b = plotly_dark(fig_b)
                    fig_b.update_traces(marker_line=dict(width=0))
                    st.plotly_chart(fig_b, use_container_width=True)

        with sub_tabs[1]:
            st.markdown("#### 📊 奇偶比分布")
            if lt == LotteryType.SSQ:
                ratio_count = Counter()
                for row in history:
                    odds = sum(1 for n in row["red"] if n % 2 == 1)
                    ratio_count[f"{odds}:{6-odds}"] += 1
                df = pd.DataFrame(ratio_count.most_common(), columns=["奇偶比", "次数"])
                fig = px.bar(df, x="奇偶比", y="次数", title="红球奇偶比分布",
                             color="次数", color_continuous_scale="Teal")
                fig = plotly_dark(fig)
                fig.update_traces(marker_line=dict(width=0))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"**最常见比例**: `{ratio_count.most_common(1)[0][0]}` "
                            f"({ratio_count.most_common(1)[0][1]}次，"
                            f"{ratio_count.most_common(1)[0][1]*100/len(history):.1f}%)")
            else:
                ratio_count = Counter()
                for row in history:
                    odds = sum(1 for n in row["front"] if n % 2 == 1)
                    ratio_count[f"{odds}:{5-odds}"] += 1
                df = pd.DataFrame(ratio_count.most_common(), columns=["奇偶比", "次数"])
                fig = px.bar(df, x="奇偶比", y="次数", title="前区奇偶比分布",
                             color="次数", color_continuous_scale="Purples_r")
                fig = plotly_dark(fig)
                fig.update_traces(marker_line=dict(width=0))
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"**最常见比例**: `{ratio_count.most_common(1)[0][0]}` "
                            f"({ratio_count.most_common(1)[0][1]}次，"
                            f"{ratio_count.most_common(1)[0][1]*100/len(history):.1f}%)")

        with sub_tabs[2]:
            st.markdown("#### 🧮 和值分布")
            if lt == LotteryType.SSQ:
                sums = [sum(row["red"]) for row in history]
            else:
                sums = [sum(row["front"]) for row in history]
            avg = sum(sums) / len(sums)
            median = sorted(sums)[len(sums) // 2]
            std = (sum((s - avg) ** 2 for s in sums) / len(sums)) ** 0.5

            sum_col1, sum_col2, sum_col3 = st.columns(3)
            with sum_col1:
                st.metric("均值", f"{avg:.1f}")
            with sum_col2:
                st.metric("中位数", f"{median}")
            with sum_col3:
                st.metric("标准差", f"{std:.1f}")

            fig = px.histogram(sums, nbins=20, title=f"和值分布 (均值={avg:.1f})",
                               labels={"value": "和值", "count": "期数"},
                               color_discrete_sequence=["#58a6ff"])
            fig = plotly_dark(fig)
            fig.update_layout(bargap=0.1, height=350)
            fig.add_vline(x=avg, line_dash="dash", line_color="#f0883e", annotation_text=f"均值={avg:.0f}")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"范围: **{min(sums)} ~ {max(sums)}** | 均值: **{avg:.1f}** | "
                        f"中位数: **{median}** | 标准差: **{std:.1f}**")

        with sub_tabs[3]:
            st.markdown("#### 🔢 尾数统计")
            if lt == LotteryType.SSQ:
                tails = Counter()
                for row in history:
                    for n in row["red"]:
                        tails[n % 10] += 1
                df = pd.DataFrame(tails.most_common(), columns=["尾数", "次数"])
                fig = px.bar(df, x="尾数", y="次数", title="红球尾数分布",
                             color="次数", color_continuous_scale="Oranges")
                fig = plotly_dark(fig)
                fig.update_traces(marker_line=dict(width=0))
                fig.update_xaxes(tickvals=df["尾数"].tolist())
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"**最热尾数**: {[f'{t}:{c}次' for t, c in tails.most_common(3)]}")
            else:
                tails = Counter()
                for row in history:
                    for n in row["front"]:
                        tails[n % 10] += 1
                df = pd.DataFrame(tails.most_common(), columns=["尾数", "次数"])
                fig = px.bar(df, x="尾数", y="次数", title="前区尾数分布",
                             color="次数", color_continuous_scale="Purples")
                fig = plotly_dark(fig)
                fig.update_traces(marker_line=dict(width=0))
                fig.update_xaxes(tickvals=df["尾数"].tolist())
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"**最热尾数**: {[f'{t}:{c}次' for t, c in tails.most_common(3)]}")

        with sub_tabs[4]:
            st.markdown("#### 🔗 重复号规律（与上期重复的号码个数）")
            repeat_counts = []
            for i in range(1, min(100, len(history))):
                if lt == LotteryType.SSQ:
                    repeats = len(set(history[i]["red"]) & set(history[i-1]["red"]))
                else:
                    repeats = len(set(history[i]["front"]) & set(history[i-1]["front"]))
                repeat_counts.append(repeats)

            rc = Counter(repeat_counts)
            total = len(repeat_counts)
            zero_repeat = rc.get(0, 0)
            one_repeat = rc.get(1, 0)
            two_repeat = rc.get(2, 0)
            three_repeat = rc.get(3, 0)

            rk_col1, rk_col2, rk_col3, rk_col4 = st.columns(4)
            with rk_col1:
                st.metric("无重复", f"{zero_repeat}期", f"{zero_repeat*100/total:.1f}%")
            with rk_col2:
                st.metric("1个重复", f"{one_repeat}期", f"{one_repeat*100/total:.1f}%")
            with rk_col3:
                st.metric("2个重复", f"{two_repeat}期", f"{two_repeat*100/total:.1f}%")
            with rk_col4:
                st.metric("3个重复", f"{three_repeat}期", f"{three_repeat*100/total:.1f}%")

            df_repeat = pd.DataFrame([
                {"重复个数": k, "期数": v, "占比": f"{v*100/total:.1f}%"} for k, v in sorted(rc.items())
            ])
            fig = px.bar(df_repeat, x="重复个数", y="期数", title="与上期重复号码个数分布",
                         color="期数", color_continuous_scale="Cividis")
            fig = plotly_dark(fig)
            fig.update_traces(marker_line=dict(width=0))
            fig.update_xaxes(tickvals=sorted(rc.keys()))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"""
            **规律发现**: 约 **{(one_repeat + two_repeat) * 100 / total:.1f}%** 的期次有 1-2 个号码与上期重复，
            这是预测时可利用的最强规律之一。纯随机生成连号反而不如利用这个重复号规律有效。
            """)
