"""
预测工具 - 封装金融预测能力
"""
from tools.finance_tool import get_finance_agent
from tools import YA_MCPServer_Tool
import logging

logger = logging.getLogger("predict_tool")

@YA_MCPServer_Tool(
    name="predict_stock_price",
    description="使用深度学习模型预测未来几天的股票价格趋势 (Amazon Chronos-Bolt)"
)
async def predict_stock_price(symbol: str, days: int = 5) -> str:
    """
    预测股票价格
    
    Args:
        symbol: 股票代码 (例如: AAPL, IBM, 0700.HK)
        days: 预测天数 (默认5天，建议不超过10天)
    
    Returns:
        JSON格式的预测结果，包含每日预测价格和置信区间
    """
    try:
        agent = get_finance_agent()
        if agent is None:
            return "金融智能体初始化失败，请检查API Key配置"
            
        # 确保session已初始化
        await agent.init_session()
        
        result = await agent.get_stock_prediction(symbol, days)
        return str(result)
        
    except Exception as e:
        logger.error(f"预测失败: {e}")
        return f"预测失败: {str(e)}"
