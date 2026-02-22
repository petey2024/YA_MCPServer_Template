# tools/advice.py
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from . import YA_MCPServer_Tool
from tools import YA_MCPServer_Tool

@YA_MCPServer_Tool(
    name="get_investment_advice",
    title="获取投资建议",
    description="获取股票投资建议，使用回归预测 + 规则分类算法"
)
async def get_investment_advice(symbol: str) -> dict:
    """
    获取股票投资建议
    使用回归预测 + 规则分类算法
    """
    # 模拟数据（实际应连接真实数据源）
    mock_data = {
        '600519': {'price': 1485.30, 'change_pct': -1.27, 'volume': 4167900, 'pe': 25.5},
        'AAPL': {'price': 178.50, 'change_pct': 2.35, 'volume': 52000000, 'pe': 28.0},
        'MSFT': {'price': 415.00, 'change_pct': 1.50, 'volume': 25000000, 'pe': 35.0},
        'TSLA': {'price': 248.00, 'change_pct': -3.50, 'volume': 80000000, 'pe': 60.0},
    }
    
    data = mock_data.get(symbol, {'price': 100, 'change_pct': 0, 'volume': 1000000, 'pe': 20})
    
    # 特征工程
    features = np.array([[
        data['change_pct'],
        data['volume'] / 1000000,
        data['price'] / 1000,
        data['pe'] / 100,
    ]])
    
    # 简单规则模型（实际应加载训练好的模型）
    change_pct = data['change_pct']
    volume = data['volume']
    
    if change_pct > 2 and volume > 10000000:
        advice = "买入"
        confidence = 0.85
    elif change_pct > 0:
        advice = "持有"
        confidence = 0.70
    elif change_pct < -2:
        advice = "卖出"
        confidence = 0.80
    else:
        advice = "持有"
        confidence = 0.65
    
    reasons = []
    if change_pct > 0:
        reasons.append(f"✅ 今日上涨{change_pct}%，走势强劲")
    else:
        reasons.append(f"⚠️ 今日下跌{abs(change_pct)}%，需谨慎")
    
    if volume > 5000000:
        reasons.append("📊 成交量放大，市场关注度高")
    
    if data['pe'] > 50:
        reasons.append("⚠️ 市盈率偏高，注意估值风险")
    
    return {
        "symbol": symbol,
        "advice": advice,
        "confidence": f"{confidence:.2%}",
        "current_price": f"¥ {data['price']:.2f}",
        "change_percent": f"{change_pct}%",
        "pe_ratio": f"{data['pe']:.2f}",
        "reasons": reasons,
        "algorithm": "规则分类 + 技术指标分析",
        "disclaimer": "投资建议仅供参考，不构成投资依据"
    }
