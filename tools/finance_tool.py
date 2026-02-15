"""
金融工具 - 将智能体能力暴露为MCP Tool
使用延迟初始化避免启动时API Key检查失败
"""

from mcp.server.models import InitializationOptions
from mcp.server.fastmcp import FastMCP
import mcp.server.stdio
import mcp.types as types
from YA_Agent.finance_agent import FinanceAgent
import logging
from tools import YA_MCPServer_Tool

logger = logging.getLogger("finance_tool")

# 使用单例模式延迟初始化，避免启动时立即检查API Key
_finance_agent_instance = None

def get_finance_agent():
    """
    获取金融智能体实例（延迟初始化）
    避免模块加载时立即实例化导致的API Key检查失败
    """
    global _finance_agent_instance
    if _finance_agent_instance is None:
        try:
            _finance_agent_instance = FinanceAgent()
            logger.info("FinanceAgent延迟初始化成功")
        except Exception as e:
            logger.error(f"FinanceAgent初始化失败: {e}")
            # 不立即抛出异常，允许工具注册但使用时返回错误
            _finance_agent_instance = None
    return _finance_agent_instance

@YA_MCPServer_Tool(
    name="get_stock_info",
    description="获取股票实时报价信息"
)
async def get_stock_info(symbol: str = "IBM") -> str:
    """
    获取股票信息
    
    Args:
        symbol: 股票代码（如AAPL, GOOGL, MSFT）
    
    Returns:
        股票价格和相关信息
    """
    try:
        agent = get_finance_agent()
        if agent is None:
            return "金融智能体初始化失败，请检查API Key配置"
            
        await agent.init_session()
        result = await agent.get_stock_quote(symbol)
        return str(result)
    except Exception as e:
        logger.error(f"获取股票信息失败: {e}")
        return f"获取股票信息失败: {str(e)}"

@YA_MCPServer_Tool(
    name="get_currency_rate", 
    description="获取货币汇率信息"
)
async def get_currency_rate(from_currency: str = "USD", to_currency: str = "CNY") -> str:
    """
    获取货币汇率
    
    Args:
        from_currency: 源货币代码（3位字母）
        to_currency: 目标货币代码（3位字母）
    
    Returns:
        实时汇率信息
    """
    try:
        agent = get_finance_agent()
        if agent is None:
            return "金融智能体初始化失败，请检查API Key配置"
            
        await agent.init_session()
        result = await agent.get_exchange_rate(from_currency, to_currency)
        return str(result)
    except Exception as e:
        logger.error(f"获取汇率失败: {e}")
        return f"获取汇率失败: {str(e)}"

@YA_MCPServer_Tool(
    name="query_finance_info",
    description="智能金融自然语言查询"
)
async def query_finance_info(query: str) -> str:
    """
    智能金融查询
    
    Args:
        query: 自然语言查询（如：苹果股票价格，美元兑人民币汇率）
    
    Returns:
        金融数据结果
    """
    try:
        agent = get_finance_agent()
        if agent is None:
            return "金融智能体初始化失败，请检查API Key配置"
            
        await agent.init_session()
        result = await agent.process(query)
        return str(result)
    except Exception as e:
        logger.error(f"金融查询失败: {e}")
        return f"金融查询失败: {str(e)}"

# 可选：添加工具列表导出（如果自动注册需要）
tools = [get_stock_info, get_currency_rate, query_finance_info]