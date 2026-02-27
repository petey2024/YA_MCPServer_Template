# Finance_Mcp_Server

本项目是一个面向金融场景的 MCP（Model Context Protocol）服务器模板：

- **Server 侧**：通过 MCP 暴露 tools/resources/prompts
- **Client 侧**：既可直接调用 MCP 工具，也可接入 DeepSeek大模型完成 tool-calling 闭环

> 典型闭环：DeepSeek（LLM）→ tool_calls → 调用 MCP Tool → 回填 Tool 结果 → DeepSeek 输出最终答案

## 组员信息

| 姓名 | 学号 | 分工 | 备注 |
| :--: | :--: | :--: | :--: |
| 孙学远 | U202414790 | 完成 MCP 服务器的基本设计 | |
| 秦硕嵘 | U202414725 | 实现 MCP 金融智能体客户端设计，添加部分功能 | |
| 史梓洋 | U202414789 | 引入 Amazon Chronos-Bolt 深度学习模型，预测股票未来价格；完成与DeepSeek大模型的交互闭环，设计Client CLI 客户端，实现端到端闭环 | |

## 快速开始

### 1) 配置

核心配置文件：

- `config.yaml`：MCP Server 元信息与 transport（stdio/sse）配置
- `env.yaml`：API Key 等运行环境配置（也支持系统环境变量，环境变量优先级更高）

常用环境变量：

- `ALPHA_VANTAGE_API_KEY`：Alpha Vantage Key（用于实时行情/汇率等）
- `DEEPSEEK_API_KEY`：DeepSeek Key（用于闭环客户端）
- `DEEPSEEK_BASE_URL`：DeepSeek OpenAI 兼容 base url（默认 `https://api.deepseek.com/v1`）
- `DEEPSEEK_MODEL`：模型名（默认 `deepseek-chat`，以控制台为准）

### 2) 启动 MCP Server（SSE）

确保 `config.yaml` 中：

- `transport.type: "sse"`
- `transport.host: "127.0.0.1"`
- `transport.port: 19420`

启动：

```bash
uv run server.py or python server.py
```

默认 SSE 地址：`http://127.0.0.1:19420/`

### 3) 使用 MCP Inspector 调试（SSE）

如果你希望在浏览器里可视化查看/调用工具，可以使用 MCP Inspector。

1）在一个终端中启动 SSE 模式的 MCP Server
```bash
uv run server.py
```

2）在另一个终端中启动 MCP Inspector：


```bash
mcp dev server.py
```

3）打开 MCP Inspector 页面后：

- 选择 `transport` 为 `sse`
- 输入服务器地址（例如 `http://127.0.0.1:19420/`）
- 在configuration中输入Proxy Session Token，这个在mcp dev server.py后会在命令行中给出
- 点击 Connect，等待连接成功
- 
> 说明：当选择 `stdio` 时，Inspector 可以自动拉起服务进程；但 `sse` 模式需要你手动先把服务端跑起来。

## 客户端（Clients）

本仓库提供两个命令行客户端：

### 1) DeepSeek 闭环客户端（推荐）

文件：`deepseek_mcp_cli.py`

用途：连接 MCP Server 拉取 tools schema → 调用 DeepSeek → 解析 tool_calls → 回调 MCP 工具 → 回填结果 → 输出最终答案。

一次性提问（展示完整过程）：

```bash
python deepseek_mcp_cli.py --query "查询今日IBM股票价格" --verbose
```

交互模式（连续提问）：

```bash
python deepseek_mcp_cli.py --verbose
```

常用参数：

- `--server-url http://127.0.0.1:19420/`：指定 MCP Server
- `--max-steps 8`：限制 tool-calling 循环次数
- `--verbose`：打印 DeepSeek 请求预览、原始响应 JSON、tool_calls 与工具返回值（API Key 会打码）

### 2) MCP 工具直连客户端（用于简单调试，不过更推荐用mcp dev server.py进入网页中进行调试）

文件：`finance_mcp_client.py`

用途：使用官方 MCP SDK 直接连接 MCP Server，并以终端 UI 方式调用工具（适合调试工具输出、验证服务可用性）。

启动：

```bash
python finance_mcp_client.py
```


## MCP 能力（Tools / Resources / Prompts）

### Tools

| 工具名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| `get_stock_info` | 获取股票实时报价信息 | `symbol: str` | 行情信息 | 数据源：Alpha Vantage |
| `get_currency_rate` | 获取货币汇率信息 | `from_currency: str`, `to_currency: str` | 汇率信息 | 数据源：Alpha Vantage |
| `query_finance_info` | 智能金融自然语言查询 | `query: str` | 按意图返回股票/汇率等数据 | |
| `predict_stock_price` | 预测未来价格趋势（Chronos-Bolt） | `symbol: str`, `days: int` | 预测结果 | |
| `get_latest_news` | 获取标的最新相关新闻（模拟） | `symbol: str`, `limit: int` | 新闻列表 | |
| `analyze_market_sentiment` | 分析市场情感倾向（模拟） | `keyword: str` | 情感分数/建议 | |
| `calculate_risk_score` | 计算股票风险评分 | `symbol: str` | 风险分数/等级 | K-Means + 加权 |
| `detect_anomaly` | 检测异常交易行为 | `symbol: str`, `days: int` | 是否异常/置信度 | Isolation Forest |
| `get_investment_advice` | 获取投资建议（模拟） | `symbol: str` | 建议/置信度/理由 | |
| `get_server_config` | 获取服务器配置项 | `key: str`, `default: Any` | 配置值 | 便于调试 |
| `greeting_tool` | 返回简单问候消息 | `name: str` | `{"message": ...}` | 基础测试 |

### Resources

| 资源名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| `finance://market/status` | 获取市场状态 | 无 | 市场状态/时间戳 | 优先真实 API，失败则降级模拟 |
| `finance://currency/list` | 获取支持的货币列表 | 无 | 货币列表 | 优先真实 API，失败则降级静态 |
| `finance://stock/symbols/{market}` | 获取指定市场股票代码 | `market: str` | 代码列表 | 支持 us/hk/cn 等 |
| `finance://stock/quote/{symbol}` | 获取股票实时报价 | `symbol: str` | 报价信息 | |
| `hello_resource` | 基础测试资源 | 无 | 示例数据 | |

### Prompts

| 指令名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| `analyze_stock_trend` | 股票趋势分析提示词 | `symbol: str`, `period: str` | 分析模板（含实时数据） | |
| `currency_arbitrage_analysis` | 货币套利分析提示词 | `base_currency: str`, `target_currencies: list` | 套利分析模板 | |
| `portfolio_risk_assessment` | 投资组合风险评估提示词 | `portfolio: dict` | 风险评估模板 | |
| `predict_price_report` | 股价预测分析报告模板 | `symbol: str`, `days: int` | 预测报告模板 | |
| `hello_prompt` | 基础测试提示词 | 无 | 示例模板 | |

## 项目结构（与当前仓库一致）

```text
YA_MCPServer_Template/
├─ server.py                      # MCP Server 启动入口（FastMCP + stdio/SSE）
├─ deepseek_mcp_cli.py            # DeepSeek ↔ MCP 闭环命令行客户端（tool-calling loop）
├─ finance_mcp_client.py          # 官方 MCP SDK 直连客户端（终端 UI）
├─ config.yaml                    # Server 元信息/transport 配置
├─ env.yaml                       # 本地环境配置（API Key 等；也支持系统环境变量）
├─ pyproject.toml                 # Python 依赖声明
├─ uv.lock                        # uv 锁定文件（可选）
├─ setup.py                       # 预留的初始化入口
├─ tools/                         # MCP Tools（通过装饰器注册）
│  ├─ __init__.py                 # 自动扫描并注册 tools 目录下的工具
│  ├─ finance_tool.py             # 行情/汇率/自然语言查询
│  ├─ predict_tool.py             # Chronos-Bolt 预测能力
│  ├─ news.py                     # 新闻与情感（模拟）
│  ├─ risk.py                     # 风险评分/异常检测
│  ├─ advice.py                   # 投资建议（模拟）
│  └─ hello_tool.py               # 基础工具（配置读取/问候）
├─ resources/                     # MCP Resources（通过装饰器注册）
│  ├─ __init__.py                 # 自动扫描并注册 resources
│  ├─ finance_resource.py         # 金融资源（优先真实 API，失败降级）
│  └─ hello_resource.py           # 示例资源
├─ prompts/                       # MCP Prompts（通过装饰器注册）
│  ├─ __init__.py                 # 自动扫描并注册 prompts
│  ├─ finance_prompt.py           # 金融分析提示模板（可含实时数据）
│  └─ hello_prompt.py             # 示例 prompt
├─ YA_Agent/                      # 智能体封装（例如 FinanceAgent）
├─ core/                          # 预测/模型相关核心逻辑
├─ modules/                       # 公共模块（连接器/适配器/工具链）
│  └─ YA_Common/
│     ├─ mcp/                     # MCPClient、Connector、OpenAI tools 适配器等
│     ├─ utils/                   # config/logger/helpers 等
│     └─ types/                   # 类型定义
└─ docs/                          # 开发指南与说明文档
```

## 备注

- 若工具涉及外部 API（Alpha Vantage / DeepSeek），请优先用系统环境变量配置 Key；`env.yaml` 适合本地开发。
