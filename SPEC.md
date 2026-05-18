# 彩票预测分析应用 SPEC

## 1. 项目概述

**名称**: lottery-predictor
**类型**: 数据分析 + 预测 + 回测 Web 应用
**功能**: 拉取近100期真实历史数据，对双色球和大乐透进行预测分析和回测
**技术栈**: Python + Streamlit + SQLite + Requests

## 2. 数据规格

### 双色球 (SSQ)
- 红球: 6个，范围 01-33，不可重复
- 蓝球: 1个，范围 01-16
- 数据源: 17500.cn

### 大乐透 (DLT)
- 前区: 5个，范围 01-35，不可重复
- 后区: 2个，范围 01-12，不可重复
- 数据源: 17500.cn

## 3. 预测规则策略

每种策略独立可配置，预测时选择单一策略或组合策略。

### 策略1: 冷热号策略 (HotColdStrategy)
- 基于近20期出现频率
- 热号策略: 优先选择出现频率最高的号码
- 冷号策略: 优先选择出现频率最低/未出现的号码
- 均衡策略: 热号+冷号混合

### 策略2: 奇偶比例策略 (OddEvenStrategy)
- 统计历史数据奇偶比分布，取最常见比例
- 双色球常见比例: 3:3, 4:2, 2:4
- 大乐通常见比例: 2:3, 3:2, 1:4

### 策略3: 区间分布策略 (ZoneStrategy)
- 将号码池划分为3-4个区间
- 每个区间至少选N个号码（可配置）
- 基于历史各区间出号数量分布

### 策略4: 和值策略 (SumRangeStrategy)
- 计算历史开奖号码和值分布
- 预测和值落在哪个区间（偏低/中间/偏高）
- 在对应和值范围内随机生成

### 策略5: 尾数策略 (DigitEndStrategy)
- 统计每个尾数(0-9)的历史出现频率
- 每期号码通常包含3-5个不同尾数
- 预测时保证尾数多样性

### 策略6: 连号历史规律策略 (ConsecutiveStrategy)
- 统计历史中连号(2连/3连)出现频率
- 按配置的概率决定是否生成连号
- 如需连号，在选号时确保有连续号码

### 策略7: AC值策略 (ACValueStrategy)
- AC值范围 6-10（双色球），预测AC值
- AC值太高/太低都是稀有情况
- 生成号码时验证AC值符合预期

### 策略8: 近期趋势策略 (TrendStrategy)
- 连续3期以上未出现的号码加权提升
- 连续3期以上出现的号码降权
- 综合评分排序后取Top号码

## 4. 回测规则

### 回测方式
- 滑动窗口: 使用前N期数据预测第N+1期
- 验证预测号码与实际开奖号码的匹配数
- 统计指标: 命中率(匹配数分布)、最大连中、最长遗漏

### 回测指标
- 一等奖命中次数(6+1 or 5+2)
- 二等奖命中次数
- 三等奖命中次数
- 红球/前区命中数分布
- 各策略历史表现对比

## 5. Web UI (Streamlit)

### 页面结构
1. **数据管理页**: 拉取/更新历史数据，显示最新100期列表
2. **预测页**: 选择彩种、选择策略、配置参数、生成预测号码
3. **回测页**: 选择策略+回测期数，显示回测统计报表
4. **历史分析页**: 冷热号排行榜、奇偶比分布、和值分布等

### 交互
- 侧边栏: 彩种切换、策略选择、参数配置
- 主区域: 数据展示、预测结果、回测图表
- 预测结果可复制

## 6. 数据存储

### SQLite 表结构
```sql
-- 双色球历史
CREATE TABLE ssq_history (
    expect TEXT PRIMARY KEY,
    date TEXT,
    red_balls TEXT,   -- "01,02,13,24,25,33"
    blue_ball TEXT,   -- "08"
    red_1 INTEGER, red_2 INTEGER, red_3 INTEGER,
    red_4 INTEGER, red_5 INTEGER, red_6 INTEGER,
    blue INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 大乐透历史
CREATE TABLE dlt_history (
    expect TEXT PRIMARY KEY,
    date TEXT,
    front_balls TEXT,  -- "01,02,13,24,25"
    back_balls TEXT,   -- "08,09"
    front_1 INTEGER, front_2 INTEGER, front_3 INTEGER,
    front_4 INTEGER, front_5 INTEGER,
    back_1 INTEGER, back_2 INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## 7. 项目结构

```
lottery/
├── SPEC.md
├── requirements.txt
├── app.py                  # Streamlit 主入口
├── fetcher/
│   ├── __init__.py
│   ├── ssq_fetcher.py      # 双色球数据抓取
│   └── dlt_fetcher.py      # 大乐透数据抓取
├── database/
│   ├── __init__.py
│   └── db.py               # SQLite 操作
├── predictor/
│   ├── __init__.py
│   ├── base.py             # 策略基类
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── hot_cold.py
│   │   ├── odd_even.py
│   │   ├── zone.py
│   │   ├── sum_range.py
│   │   ├── digit_end.py
│   │   ├── consecutive.py
│   │   ├── ac_value.py
│   │   └── trend.py
│   └── engine.py           # 预测引擎
├── backtest/
│   ├── __init__.py
│   └── engine.py           # 回测引擎
├── pages/
│   ├── data_manager.py
│   ├── prediction.py
│   ├── backtest.py
│   └── analysis.py
└── utils/
    ├── __init__.py
    └── helpers.py
```
