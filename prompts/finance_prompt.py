"""
金融相关提示词
提供基于真实API数据的金融分析提示模板
修复API Key配置和路径查找问题
"""

from prompts import YA_MCPServer_Prompt
from mcp.server.fastmcp import FastMCP
from mcp.types import Prompt
import json
import aiohttp
import os
import yaml
from datetime import datetime
import logging

logger = logging.getLogger("finance_prompts")

# 初始化MCP实例
mcp = FastMCP("FinancePrompts")

# 修正：设置正确的API基础URL
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
# 使用单例模式避免重复创建session
_api_session = None

async def _get_api_session():
    """获取共享的API会话"""
    global _api_session
    if _api_session is None:
        _api_session = aiohttp.ClientSession()
    return _api_session

async def _get_api_key() -> str:
    """
    获取API Key，支持多种配置源 - 增强版本
    """
    # 1. 从环境变量获取（最高优先级）
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if api_key and api_key.strip() and api_key != "demo":
        logger.info("✓ 从系统环境变量获取API Key")
        return api_key.strip()
    
    # 2. 从env.yaml文件获取
    try:
        # 使用更可靠的路径查找方法
        current_file = os.path.abspath(__file__)
        # 假设env.yaml在项目根目录（resources上级的上级）
        project_root = os.path.dirname(os.path.dirname(current_file))
        config_path = os.path.join(project_root, "env.yaml")
        
        logger.info(f"尝试从配置文件加载: {config_path}")
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                yaml_key = config.get("ALPHA_VANTAGE_API_KEY")
                if yaml_key and yaml_key.strip() and yaml_key != "demo":
                    logger.info("✓ 从env.yaml文件获取API Key")
                    return yaml_key.strip()
                else:
                    logger.warning("env.yaml中的API Key为空或为demo")
        else:
            logger.warning(f"配置文件不存在: {config_path}")
            
    except Exception as e:
        logger.error(f"读取env.yaml失败: {e}")
    
    return None

async def _make_api_request(params: dict) -> dict:
    """
    发送API请求 - 修正版本
    """
    api_key = await _get_api_key()
    if not api_key:
        return {"error": "API Key未配置，请在env.yaml中设置ALPHA_VANTAGE_API_KEY"}
    
    params["apikey"] = api_key
    
    try:
        session = await _get_api_session()
        async with session.get(ALPHA_VANTAGE_BASE_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                # 检查API返回的错误信息
                if "Error Message" in data:
                    logger.error(f"API返回错误: {data['Error Message']}")
                    return {"error": data["Error Message"]}
                elif "Note" in data:
                    logger.warning(f"API限制: {data['Note']}")
                    return {"error": f"API调用频率限制: {data['Note']}"}
                else:
                    return data
            else:
                error_msg = f"API请求失败，状态码: {response.status}"
                logger.error(error_msg)
                return {"error": error_msg}
    except Exception as e:
        error_msg = f"网络请求错误: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}


@YA_MCPServer_Prompt()
async def analyze_stock_trend(symbol: str, period: str = "1month") -> str:
    """
    股票趋势分析提示词（基于真实API数据）
    
    Args:
        symbol: 股票代码
        period: 分析周期（1week, 1month, 3months）
    
    Returns:
        包含实时数据的分析提示词
    """
    try:
        # 1. 获取实时股票数据
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        
        api_result = await _make_api_request(params)
        
        # 2. 构建基于真实数据的提示词
        if "error" in api_result:
            data_section = f"⚠️ 无法获取实时数据: {api_result['error']}\n使用历史分析模板。"
        else:
            quote = api_result.get("Global Quote", {})
            current_price = quote.get("05. price", "未知")
            change = quote.get("09. change", "未知")
            change_percent = quote.get("10. change percent", "未知")
            
            data_section = f"""
📊 实时数据（{datetime.now().strftime('%Y-%m-%d %H:%M')}）：
- 当前价格: {current_price}
- 涨跌幅: {change} ({change_percent})
- 最后更新: {quote.get('07. latest trading day', '未知')}
"""
        
        # 3. 返回包含实时数据的提示词
        return f"""
{data_section}

请分析股票 {symbol} 在过去 {period} 的表现趋势：

1. **技术分析**：
   - 计算移动平均线（MA20, MA50）
   - 识别支撑位和阻力位
   - 分析交易量变化趋势

2. **基本面评估**：
   - 评估公司财务状况
   - 分析行业竞争地位
   - 考虑宏观经济影响因素

3. **投资建议**：
   - 短期操作策略（1-7天）
   - 中期持有建议（1-3个月）
   - 风险等级评估（低/中/高）

请以专业金融分析师的角度提供详细分析，并引用最新市场数据。
"""
    except Exception as e:
        return f"生成分析提示词失败: {str(e)}"

@YA_MCPServer_Prompt()
async def currency_arbitrage_analysis(base_currency: str, target_currencies: list) -> str:
    """
    货币套利分析提示词（基于真实汇率数据）
    
    Args:
        base_currency: 基础货币（如USD）
        target_currencies: 目标货币列表（如["CNY", "EUR", "JPY"]）
    
    Returns:
        包含实时汇率的套利分析提示词
    """
    try:
        # 1. 获取实时汇率数据
        exchange_rates = {}
        
        for target_currency in target_currencies:
            params = {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": base_currency,
                "to_currency": target_currency
            }
            
            api_result = await _make_api_request(params)
            
            if "error" not in api_result:
                rate_data = api_result.get("Realtime Currency Exchange Rate", {})
                exchange_rates[target_currency] = {
                    "rate": rate_data.get("5. Exchange Rate"),
                    "bid": rate_data.get("8. Bid Price"),
                    "ask": rate_data.get("9. Ask Price"),
                    "time": rate_data.get("6. Last Refreshed")
                }
        
        # 2. 构建实时数据部分
        rates_section = "📈 实时汇率数据：\n"
        for currency, data in exchange_rates.items():
            rates_section += f"- {base_currency}/{currency}: {data.get('rate', '未知')} (买价: {data.get('bid')}/卖价: {data.get('ask')})\n"
        
        if not exchange_rates:
            rates_section = "⚠️ 无法获取实时汇率数据，使用理论分析框架。\n"
        
        # 3. 返回包含实时数据的提示词
        currencies_str = ", ".join(target_currencies)
        return f"""
{rates_section}

请分析 {base_currency} 对 {currencies_str} 的套利机会：

**套利策略分析**：
1. **直接套利**：
   - 计算直接汇率差异
   - 识别价格偏差机会

2. **三角套利**：
   - 分析交叉汇率关系
   - 寻找无风险套利路径

3. **风险因素**：
   - 汇率波动性评估
   - 交易成本计算（点差+手续费）
   - 执行时间窗口限制

4. **策略建议**：
   - 推荐套利路径
   - 预期收益率估算
   - 风险控制措施

请基于最新市场数据提供具体可执行的套利策略。
"""
    except Exception as e:
        return f"生成套利分析提示词失败: {str(e)}"

@YA_MCPServer_Prompt()
async def portfolio_risk_assessment(portfolio: dict) -> str:
    """
    投资组合风险评估提示词（增强版本）
    
    Args:
        portfolio: 投资组合字典（如 {{"AAPL": 0.3, "TSLA": 0.2, "现金": 0.5}}）
    
    Returns:
        基于实时数据的风险评估提示词
    """
    try:
        # 1. 获取投资组合中股票的实时数据
        stock_data = {}
        
        for symbol, weight in portfolio.items():
            if symbol not in ["现金", "cash", "Cash"]:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol
                }
                
                api_result = await _make_api_request(params)
                if "error" not in api_result:
                    quote = api_result.get("Global Quote", {})
                    stock_data[symbol] = {
                        "price": quote.get("05. price"),
                        "change": quote.get("09. change"),
                        "volume": quote.get("06. volume"),
                        "weight": weight
                    }
        
        # 2. 构建实时数据部分
        portfolio_section = "📊 投资组合实时数据：\n"
        for symbol, data in stock_data.items():
            portfolio_section += f"- {symbol}: 价格={data['price']}, 权重={data['weight']*100}%\n"
        
        if not stock_data:
            portfolio_section = "⚠️ 无法获取实时股价数据，使用静态分析框架。\n"
        
        # 3. 返回增强的提示词
        portfolio_str = json.dumps(portfolio, ensure_ascii=False)
        return f"""
{portfolio_section}

请对以下投资组合进行全面的风险评估：
{portfolio_str}

**风险评估维度**：

1. **市场风险**：
   - 系统性风险（Beta系数）
   - 非系统性风险（个股特异性风险）
   - 相关性分析

2. **流动性风险**：
   - 资产变现能力评估
   - 市场深度分析
   - 极端情况流动性压力测试

3. **集中度风险**：
   - 行业集中度
   - 个股集中度
   - 货币风险（如有外币资产）

4. **风险量化指标**：
   - 计算VaR（风险价值）
   - 最大回撤分析
   - 夏普比率评估

5. **优化建议**：
   - 风险分散策略
   - 对冲方案设计
   - 动态再平衡计划

请基于最新市场数据提供专业的风险评估报告。
"""
    except Exception as e:
        return f"生成风险评估提示词失败: {str(e)}"

# 导出提示词列表
prompts = [analyze_stock_trend, currency_arbitrage_analysis, portfolio_risk_assessment]