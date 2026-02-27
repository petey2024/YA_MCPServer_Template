## Finance_Mcp_Server

[一句话功能简介]
本项目是一个融合深度学习与传统量化分析的智能金融 MCP 服务器。它集成 Alpha Vantage API 提供实时行情查询，引入了Amazon Chronos-Bolt深度学习模型进行股价趋势预测，并结合情感分析、风险评分及异常检测等 AI 算法，提供股票查询、汇率转换、市场分析等金融数据服务。
### 组员信息

| 姓名 | 学号 | 分工 | 备注 |
| :--: | :--: | :--: | :--: |
|孙学远|U202414790|完成MCP服务器的基本设计|      |
|秦硕嵘|U202414725|实现MCP金融智能体的客户端设计，添加部分功能|      |
|史梓洋|U202414789|引入深度学习模型Amazon Chronos-Bolt，添加股票价格趋势预测功能|      |

### Tool 列表

| 工具名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| `get_stock_info` | 获取股票实时报价 | `symbol: str` (股票代码) | 股票价格、涨跌幅、成交量等 | 支持中英文股票名映射 |
| `get_currency_rate` | 获取货币汇率 | `from_currency: str`, `to_currency: str` (货币代码) | 实时汇率、买卖价格、时间戳 | 支持USD/CNY等主流货币 |
| `query_finance_info` | 智能金融查询 | `query: str` (自然语言查询) | 根据查询类型返回相应金融数据 | 自动识别股票/汇率查询意图 |
| `hello_tool` | 基础测试工具 | 无 | 服务器基本信息 | 用于验证服务器运行状态 |
|`greeting_tool`| 返回简单的问候消息 | 无 (或` name: str`) |问候语 `message` | 基础测试工具 |
| `get_latest_news` |获取标的最新相关新闻| 	`symbol: str`, `limit: int` | 新闻标题、内容、时间 | 支持主流财经源 |
| `analyze_market_sentiment`|分析特定关键词的市场情感倾向 | `text: str` (文本/关键词) | 情感倾向、置信度分数 | NLP 情感分析 |
| `calculate_risk_score` | 计算股票风险评分| 	`symbol: str` (股票代码) | 风险分数、风险等级 | 使用 K-Means 聚类 + 加权评分算法 |
| `detect_anomaly` |检测异常交易行为 | `data: list` (交易数据) | 风险情况 | 使用 Isolation Forest 异常检测算法 |
| `predict_stock_price` | 预测股票价格趋势 | `symbol: str` (代码), `days: int` (天数) | 价格预测、趋势方向、置信区间 | 基于 Amazon Chronos-Bolt 深度学习模型 |


### Resource 列表

| 资源名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| `finance://market/status` | 获取全球市场状态 | 无 | 各市场开市状态、时间戳 | 实时更新市场状态信息 |
| `finance://currency/list` | 获取支持的货币列表 | 无 | 货币代码、名称、符号列表 | 包含主流货币信息 |
| `finance://stock/symbols/{market}` | 获取指定市场股票代码 | `market: str` (市场标识) | 该市场股票代码列表 | 支持us/hk/cn市场 |
| `finance://stock/quote/{symbol}` | 获取股票实时报价 | `symbol: str` (股票代码) | 实时价格、涨跌幅、成交量、时间戳 | 
| `hello_resource` | 基础测试资源 | 无 | 示例资源数据 | 用于验证资源功能 |

### Prompts 列表

| 指令名称 | 功能描述 | 输入 | 输出 | 备注 |
| :------: | :------: | :--: | :--: | :--: |
| `analyze_stock_trend` | 股票趋势分析提示 | `symbol: str`, `period: str` (周期) | 专业股票分析报告 | 提供技术指标和投资建议 |
| `currency_arbitrage_analysis` | 货币套利机会分析 | `base_currency: str`, `target_currencies: list` | 套利策略和风险评估 | 识别交叉汇率套利机会 |
| `portfolio_risk_assessment` | 投资组合风险评估 | `portfolio: dict` (资产配置) | 风险评分和缓解建议 | 多维风险评估体系 |
| `predict_price_report` | 股价预测分析报告 | `symbol: str`, `days: int` (预测天数) | 深度学习预测简报 | 基于Chronos-Bolt模型上下文 |
| `hello_prompt` | 基础测试提示词 | 无 | 示例提示模板 | 用于验证提示词功能 |

### 项目结构

- `core/`: 核心业务逻辑模块
  - `base_agent.py`: 智能体基类，提供通用接口
  - `finance_agent.py`: 金融数据智能体实现
  - `predictor.py`: 深度学习预测模块 (封装 Amazon Chronos-Bolt)
  
- `tools/`: MCP工具模块
  - `hello_tool.py`: 基础测试工具
  - `finance_tool.py`: 金融数据处理工具
  - `predict_tool.py`: 股票预测工具
  
- `resources/`: MCP资源模块  
  - `hello_resource.py`: 基础测试资源
  - `finance_resource.py`: 金融数据资源
  
- `prompts/`: MCP提示词模块
  - `hello_prompt.py`: 基础提示词
  - `finance_prompt.py`: 金融分析提示词
  
- `config.yaml`: 服务器配置文件（添加金融API配置、日志配置等额外配置）
- `env.yaml`: 环境变量配置文件（包含API密钥等敏感信息）
- `server.py`: 服务器启动入口文件
- `requirements.txt`: 项目依赖列表

### 其他需要说明的情况

## DeepSeek 闭环（命令行客户端）

本项目的 MCP Server 负责暴露工具（tools/resources/prompts）。
若要让 AI 大模型自动调用这些工具并把结果整合成最终回答，需要一个“闭环客户端（Bridge Client）”来做编排：

DeepSeek（LLM）→ 返回 tool_calls → 调用 MCP 工具 → 回填 tool 结果 → DeepSeek 输出最终回答

仓库已提供命令行版闭环客户端：`deepseek_mcp_cli.py`。

### 1) 配置 DeepSeek

在系统环境变量或 `env.yaml` 中配置（推荐用环境变量）：

- `DEEPSEEK_API_KEY`: 你的 DeepSeek API Key
- `DEEPSEEK_BASE_URL`: OpenAI 兼容接口 base url（默认 `https://api.deepseek.com/v1`）
- `DEEPSEEK_MODEL`: 模型名（默认 `deepseek-chat`，以你的控制台为准）

### 2) 启动 MCP Server（SSE）

确保 [config.yaml](config.yaml) 中：

- `transport.type: "sse"`
- `transport.host: "127.0.0.1"`
- `transport.port: 19420`

启动：

`python server.py`

### 3) 运行闭环客户端（展示完整调用流程）

一次性提问：

`python deepseek_mcp_cli.py --query "查询 AAPL 最新价格，并结合新闻与风险评分给出建议" --verbose`

说明：

- `--verbose` 会打印 DeepSeek 请求预览、原始响应 JSON、每次 tool_calls 以及工具返回值（对 API Key 会打码）。
- 如需指定 MCP Server：`--server-url http://127.0.0.1:19420/`

交互模式（连续提问）：

`python deepseek_mcp_cli.py --verbose`

### 密钥管理
- `ALPHA_VANTAGE_API_KEY`: Alpha Vantage金融数据API访问密钥
- 所有密钥通过环境变量或加密配置文件管理，确保安全性

### 技术框架
- **集成 PyTorch 深度学习框架**
- **使用了 Amazon Chronos-Forecasting**
- 主要基于 **MCP** 协议
- 使用 **aiohttp** 进行异步HTTP请求处理

### 模型使用
- 使用 Amazon Chronos-Bolt 深度学习模型
- 实现零样本时间序列预测
- 以 Alpha Vantage 获取的历史收盘价为输入，预测未来股价趋势及置信区间
- 专注于金融数据的获取、处理和标准化输出
- 结合传统金融分析方法与前沿深度学习技术
