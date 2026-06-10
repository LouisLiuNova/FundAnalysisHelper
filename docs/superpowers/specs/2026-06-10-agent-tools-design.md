# Agent Tool Calling 设计规范

> 日期: 2026-06-10
> 状态: 设计中
> 依赖: Backend MVP (全部 19 Tasks 已完成)

## 目标

为 FundAnalysisHelper 的 7 位分析师 Agent 引入工具调用机制，使其能自主按需调用 AKshare / Tushare Composite 数据源，而非完全依赖
`fetch_data_node` 的一次性预取。

## 总体架构

**预取 + 工具按需调用（A+B 混合模式）**

- `fetch_data_node` 保留：预取通用数据（basic info, 90 日 NAV, Shibor）
- 每位分析师节点内部嵌入 ReAct 工具调用循环（最多 3 轮）
- 辩论、CIO、报告编写节点不变，不使用工具

```
                       fetch_data_node（预取，一次）
                       ├─ get_fund_basic(code)
                       ├─ get_fund_nav(code, days=90)
                       └─ get_macro("shibor")
                               ↓
                    fund_data 注入 GraphState
                               ↓
       ┌───────────────────────┼───────────────────────┐
       │   7 位分析师并行（每个节点内部 = Agent 工具循环）  │
       │                                                   │
       │   agent.run_with_tools(message, tools, context)   │
       │   ┌──────────────────────────────────┐           │
       │   │ 🔄 ReAct 循环（最多 3 轮）         │           │
       │   │  LLM(bind_tools(tools))           │           │
       │   │  → tool_call? → execute → LLM     │           │
       │   │  → 无 tool_call → 返回分析报告     │           │
       │   └──────────────────────────────────┘           │
       └───────────────────────┬───────────────────────┘
                               ↓
                   bull → bear（辩论，无工具）
                               ↓
                   CIO → reporter（无工具）
```

## 工具定义

### 工具清单

| 工具名 | 封装的数据源方法 | 参数 | 返回内容 |
|--------|----------------|------|---------|
| `get_fund_nav_detail` | `ds.get_fund_nav(code, days)` | `code: str, days: int = 365` | 扩展净值历史（单位净值 + 累计净值） |
| `get_fund_portfolio` | `ds.get_fund_portfolio(code)` | `code: str` | 前十大重仓股（股票代码/名称/占净值比/持股数/市值） |
| `get_sector_allocation` | `ds.get_fund_portfolio_industry_allocation(code)` ⚠️ 新增 | `code: str` | 行业分布（行业类别/占净值比/市值） |
| `get_fund_manager` | `ds.get_fund_manager(code)` | `code: str` | 经理背景/经验/风格/在管产品 |
| `get_macro_cpi` | `ds.get_macro("cpi")` | 无 | CPI 年率历史 |
| `get_macro_gdp` | `ds.get_macro("gdp")` | 无 | GDP 年率历史 |
| `get_fund_announcements` | `ds.get_fund_announcements(code)` ⚠️ 新增 | `code: str, limit: int = 5` | 基金近期公告（标题/日期） |

### 工具分组与分配

```
通用组 → 全部 7 位分析师
├─ get_fund_nav_detail

组合组 → 行业配置分析师
├─ get_fund_portfolio
└─ get_sector_allocation

经理组 → 基金经理分析师
└─ get_fund_manager

宏观组 → 宏观经济分析师
├─ get_macro_cpi
└─ get_macro_gdp

资讯组 → 新闻事件分析师、市场情绪分析师
└─ get_fund_announcements
```

| 分析师 | 工具组 | 具体工具 |
|--------|--------|---------|
| 基本面分析师 | 通用 | `get_fund_nav_detail` |
| 技术面分析师 | 通用 | `get_fund_nav_detail` |
| 行业配置分析师 | 通用 + 组合 | `get_fund_nav_detail` + `get_fund_portfolio` + `get_sector_allocation` |
| 基金经理分析师 | 通用 + 经理 | `get_fund_nav_detail` + `get_fund_manager` |
| 市场情绪分析师 | 通用 + 资讯 | `get_fund_nav_detail` + `get_fund_announcements` |
| 新闻事件分析师 | 通用 + 资讯 | `get_fund_nav_detail` + `get_fund_announcements` |
| 宏观经济分析师 | 通用 + 宏观 | `get_fund_nav_detail` + `get_macro_cpi` + `get_macro_gdp` |

## BaseAgent 重构

### 新增方法: `run_with_tools()`

```python
async def run_with_tools(
    self,
    user_message: str,
    tools: list[Callable],
    context: dict | None = None,
    max_rounds: int = 3,
) -> str:
```

**循环逻辑:**

1. 初始化消息列表: `[SystemMessage(prompt), HumanMessage(user_message + context)]`
2. `llm_with_tools = self._llm.bind_tools(tools)`
3. `response = await llm_with_tools.ainvoke(messages)`
4. 如果有 `tool_calls` 且未达 `max_rounds`:
   - 执行工具，将结果作为 `ToolMessage` 追加到消息列表
   - 回到步骤 3
5. 无 `tool_calls` 或达到 `max_rounds` → 返回 `response.content`

### 保留方法: `invoke()`

原有 `invoke()` 不变，辩论、CIO、报告编写仍使用此方法。

## 工具模块组织

文件: `backend/app/agents/tools.py`

```python
# 工具定义：每个 @tool 函数封装一个数据源方法
# 工具分组：TOOL_GROUPS dict
# Agent 映射：AGENT_TOOL_MAP dict
# 工厂函数：get_tools_for_agent(agent_type: str) -> list[Callable]
```

工具函数内部通过 `get_datasource()` 获取当前数据源实例，数据源在
`AnalysisService._ensure_initialized()` 中已注入。

## 数据源扩展

### 新增抽象方法（BaseDataSource）

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `get_fund_portfolio_industry_allocation(code)` | `list[dict]` | 行业配置详情 |
| `get_fund_announcements(code, limit=5)` | `list[dict]` | 基金近期公告 |

### 各适配器实现

| 方法 | AKshareAdapter | TushareAdapter |
|------|---------------|---------------|
| `get_fund_portfolio_industry_allocation` | `fund_portfolio_industry_allocation_em(symbol, date)` | 返回空（无对应 API） |
| `get_fund_announcements` | `fund_announcement_report_em(symbol)` | 返回空（无对应 API） |

### CompositeDataSource

两个新方法遵循现有模式：AKshare 主查 → Tushare 兜底。

## Workflow 集成

### `analyst_node` 改动

```python
async def analyst_node(state: GraphState, analyst_type: str) -> dict:
    config = get_config()
    agent = classes[analyst_type](model=..., base_url=..., api_key=...)
    tools = get_tools_for_agent(analyst_type)

    result = await agent.run_with_tools(
        user_message=f"请对基金 {fund_name}（{fund_code}）进行分析...",
        tools=tools,
        context=state.get("fund_data", {}),
        max_rounds=3,
    )
    return {"analyst_reports": {analyst_type: result}}
```

### 不修改的部分

- `fetch_data_node` — 保留，预取通用数据
- `bull_node` / `bear_node` — 辩论不用工具
- `cio_node` — CIO 裁决不用工具
- `reporter_node` — 报告编写不用工具
- `compile_workflow()` — DAG 结构不变

## 与已知限制

### 新闻/情绪数据缺口

- `search_fund_news` 无法实现（AKshare 无基金新闻 API）。降级为 `get_fund_announcements`。
- 市场情绪分析师无专用 API（`fund_scale_change_em` 返回汇总数据，无法按基金代码过滤）。
  该分析师仅依赖预取 NAV + 公告工具。
- 预留扩展点：后续可接入外部搜索引擎或 RSS。

### 工具执行错误处理

- 单个工具失败：返回错误信息作为 `ToolMessage`，LLM 决定下一步
- 全部工具失败：Agent 基于预取数据继续分析（优雅降级）
- 循环超时：`max_rounds` 到达后强制返回

## 涉及文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/agents/tools.py` | **新建** | 7 个工具定义 + 分组 + 映射 + 工厂函数 |
| `backend/app/agents/base.py` | **修改** | 新增 `run_with_tools()` 方法 |
| `backend/app/graph/workflow.py` | **修改** | `analyst_node` 改用 `run_with_tools()` |
| `backend/app/datasource/base.py` | **修改** | 新增 2 个抽象方法 |
| `backend/app/datasource/akshare_adapter.py` | **修改** | 实现 2 个新方法 |
| `backend/app/datasource/tushare.py` | **修改** | 实现 2 个新方法（返回空或尽力而为） |
| `backend/app/datasource/composite.py` | **修改** | 实现 2 个新方法的 fallback 逻辑 |
| `backend/app/agents/analysts/*.py` | **不变** | `analyze()` 方法保留（其他节点可能用到） |
| `backend/tests/test_agent_tools.py` | **新建** | 工具定义 + 分组 + 工厂函数测试 |
| `backend/tests/test_base_agent_tools.py` | **新建** | `run_with_tools()` 循环逻辑测试 |
| `backend/tests/test_akshare_adapter.py` | **修改** | 新增 2 个方法的测试 |
| `backend/tests/test_composite_datasource.py` | **修改** | 新增 2 个方法的 composite 测试 |
