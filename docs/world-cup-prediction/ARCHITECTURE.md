# 世界杯预测小程序架构设计

版本：v0.1  
更新时间：2026-06-13

## 1. 架构目标

系统目标是支持低频数据更新、赛前预测、AI 情报抽取和小程序展示。

设计原则：

- 不做秒级实时比分。
- 小程序只访问后端 API，不直接访问外部数据源。
- 所有外部数据先入库和快照，再进入特征工程。
- LLM 只负责新闻理解、结构化抽取和解释生成，不直接决定胜负概率。
- 预测模型使用可回测、可校准的小模型。

## 2. 总体架构

```mermaid
flowchart TD
    A["外部数据源"] --> B["采集任务"]
    B --> C["Raw 快照存储"]
    C --> D["清洗归一化"]
    D --> E["PostgreSQL 标准数据"]
    E --> F["特征工程"]
    E --> G["AI 情报抽取"]
    G --> F
    F --> H["模型服务"]
    H --> I["比分概率"]
    H --> J["赛事模拟"]
    I --> K["预测结果缓存"]
    J --> K
    G --> L["AI 解读"]
    K --> M["API 服务"]
    L --> M
    M --> N["微信小程序"]
    O["管理后台"] --> E
    O --> H
```

## 3. 数据源

### 3.1 主数据源

生产建议接授权数据源：

```text
Sportmonks
API-Football
```

主要用于：

```text
赛程
比分
阵容
伤停
球员赛季统计
比赛技术统计
```

### 3.2 补充数据源

懂球帝适合作为中文数据补充和原型数据源。

已确认：

```text
世界杯 cid = 61
世界杯 season_id = 26123
```

可用接口形态：

```text
赛程：
/sport-data/soccer/biz/data/schedule?season_id=26123&app=dqd&version=853&platform=ios&language=zh-cn&round_all=1

积分榜：
/sport-data/soccer/biz/data/standing?season_id=26123&app=dqd&version=850&platform=ios&language=zh-cn

球员榜：
/sport-data/soccer/biz/data/person_ranking?season_id=26123&app=dqd&type=goals&language=zh-cn

阵容：
/sport-data/soccer/biz/dqd/bkb_match/lineup/{match_id}?app=dqd&lang=zh-cn
```

### 3.3 历史训练数据

```text
Fjelstul World Cup Database
Kaggle International Football Results
StatsBomb Open Data
FIFA Ranking
World Football Elo Ratings
```

### 3.4 新闻和环境数据

```text
懂球帝资讯
FIFA 新闻
球队官方公告
NewsAPI / GDELT
Open-Meteo
FIFA 场馆信息
```

## 4. 数据更新流程

```mermaid
sequenceDiagram
    participant Scheduler as 定时任务
    participant Collector as 采集器
    participant Raw as Raw 快照
    participant DB as PostgreSQL
    participant AI as AI 情报服务
    participant Feature as 特征服务
    participant Model as 模型服务
    participant Cache as Redis

    Scheduler->>Collector: 触发采集
    Collector->>Raw: 保存原始响应
    Collector->>DB: 写入标准数据
    DB->>AI: 提供新闻和上下文
    AI->>DB: 写入结构化情报
    DB->>Feature: 生成比赛特征
    Feature->>Model: 请求预测
    Model->>DB: 保存预测结果
    Model->>Cache: 写入展示缓存
```

更新频率：

```text
每天凌晨：
  赛程、积分榜、球员榜、球队榜、新闻

比赛前 24 小时：
  伤停、预计首发、天气、AI 情报

比赛前 3 小时：
  关键情报、最终赛前预测

比赛后：
  赛果、积分榜、球员数据、模型复盘
```

## 5. 后端模块

### 5.1 collector-service

职责：

```text
拉取外部数据
保存原始 JSON / HTML 快照
记录采集成功或失败
控制频率和重试
```

### 5.2 normalizer-service

职责：

```text
统一球队 ID
统一球员 ID
清洗中文名和英文名
处理时间格式
标准化比赛状态
```

### 5.3 ai-insight-service

职责：

```text
读取新闻
抽取伤停、停赛、战术、教练言论
输出结构化 impact_score
生成预测解释
检查数据冲突
```

### 5.4 feature-service

职责：

```text
生成单场比赛特征
聚合球队近期状态
聚合球员近期状态
计算阵容稳定性
计算环境影响
```

### 5.5 model-service

职责：

```text
训练胜平负模型
训练进球期望模型
生成单场预测
输出比分概率
进行概率校准
记录模型版本
```

### 5.6 simulation-service

职责：

```text
读取单场预测概率
模拟小组赛和淘汰赛
输出出线、晋级、冠军概率
```

### 5.7 api-service

职责：

```text
给小程序提供接口
读取 Redis 缓存
返回比赛、球队、球员、预测和模拟结果
```

## 6. 数据库核心表

```text
teams
players
matches
venues
coaches
raw_snapshots
team_stats_snapshots
player_stats_snapshots
news_items
ai_insights
model_features
model_versions
match_predictions
tournament_simulations
prediction_reviews
```

关键表说明：

```text
raw_snapshots：
  保存外部接口原始数据，方便追溯。

model_features：
  保存每次预测时输入模型的特征快照。

match_predictions：
  保存每场比赛不同时间点的预测结果。

model_versions：
  保存模型版本、训练数据范围、评估指标。

tournament_simulations：
  保存赛事模拟结果，包括出线和冠军概率。
```

## 7. 模型架构

```mermaid
flowchart TD
    A["历史比赛数据"] --> B["训练特征"]
    B --> C["胜平负模型"]
    B --> D["进球期望模型"]
    E["赛前最新特征"] --> C
    E --> D
    C --> F["胜平负概率"]
    D --> G["期望进球"]
    G --> H["泊松比分分布"]
    F --> I["蒙特卡洛模拟"]
    H --> I
```

模型清单：

```text
胜平负模型：
  LightGBM / CatBoost / Logistic Regression baseline

进球期望模型：
  Poisson / Dixon-Coles / LightGBM Regressor

赛事模拟：
  Monte Carlo Simulation
```

评估指标：

```text
Log Loss
Brier Score
Calibration Error
Top-1 Accuracy
比分 Top 5 覆盖率
```

## 8. 小程序访问架构

```mermaid
flowchart LR
    A["微信小程序"] --> B["API Gateway / 后端 API"]
    B --> C["Redis"]
    B --> D["PostgreSQL"]
    C --> E["预测缓存"]
    D --> F["基础数据"]
    D --> G["赛后复盘"]
```

小程序不直接访问：

```text
懂球帝
FIFA
商业体育 API
新闻 API
OpenAI API
模型服务内部接口
```

## 9. 推荐技术栈

```text
小程序：
  微信原生 / Taro

后端：
  FastAPI

模型：
  Python
  LightGBM
  CatBoost
  scikit-learn

数据库：
  PostgreSQL

缓存：
  Redis

任务调度：
  APScheduler / Celery

AI：
  OpenAI API

部署：
  腾讯云 / 阿里云
  对象存储保存 Raw 快照
```

## 10. MVP 架构落地顺序

第一步：

```text
FastAPI 后端
PostgreSQL
懂球帝赛程、积分榜、球员榜采集
基础 API
```

第二步：

```text
历史比赛导入
Elo 计算
LightGBM baseline
Poisson 比分模型
```

第三步：

```text
AI 新闻抽取
AI 解读生成
match_predictions 入库
```

第四步：

```text
小程序首页
比赛详情页
小组页
预测榜
```

第五步：

```text
管理后台
人工审核
模型复盘
商业数据源替换
```

