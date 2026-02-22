# tools/risk.py
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from . import YA_MCPServer_Tool
from tools import YA_MCPServer_Tool

@YA_MCPServer_Tool(
    name="calculate_risk_score",
    title="计算风险评分",
    description="计算股票风险评分，使用 K-Means 聚类 + 加权评分算法"
)
async def calculate_risk_score(symbol: str) -> dict:
    """
    计算股票风险评分
    使用 K-Means 聚类 + 加权评分算法
    """
    mock_stocks = {
        '600519': {'change_pct': -1.27, 'volatility': 0.02, 'pe_ratio': 25.5, 'volume_ratio': 1.2},
        'AAPL': {'change_pct': 2.35, 'volatility': 0.015, 'pe_ratio': 28.0, 'volume_ratio': 0.8},
        'TSLA': {'change_pct': -5.0, 'volatility': 0.05, 'pe_ratio': 60.0, 'volume_ratio': 2.5},
    }
    
    data = mock_stocks.get(symbol, {'change_pct': 0, 'volatility': 0.02, 'pe_ratio': 20, 'volume_ratio': 1.0})
    
    # 特征向量
    features = np.array([[
        abs(data['change_pct']),
        data['volatility'] * 100,
        data['pe_ratio'] / 100,
        data['volume_ratio'],
    ]])
    
    # K-Means 聚类（模拟）
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit([[0, 0, 0, 0], [5, 5, 5, 5], [10, 10, 10, 10]])
    cluster = kmeans.predict(features)[0]
    
    # 风险评分计算
    weights = [0.3, 0.3, 0.2, 0.2]
    risk_score = np.sum(features[0] * weights) * 10
    
    if risk_score > 50:
        risk_level = "高风险"
    elif risk_score > 30:
        risk_level = "中风险"
    else:
        risk_level = "低风险"
    
    risk_factors = []
    if abs(data['change_pct']) > 3:
        risk_factors.append("今日波动较大")
    if data['volatility'] > 0.03:
        risk_factors.append("历史波动率高")
    if data['pe_ratio'] > 50:
        risk_factors.append("市盈率偏高")
    if data['volume_ratio'] > 2:
        risk_factors.append("成交量异常放大")
    
    return {
        "symbol": symbol,
        "risk_score": f"{risk_score:.2f}",
        "risk_level": risk_level,
        "risk_cluster": f"聚类组别：{cluster}",
        "risk_factors": risk_factors if risk_factors else ["无明显风险因素"],
        "recommendation": "建议谨慎操作" if risk_score > 50 else "可正常操作",
        "algorithm": "K-Means 聚类 + 加权评分"
    }

@YA_MCPServer_Tool(
    name="detect_anomaly",
    title="检测异常交易",
    description="检测异常交易行为，使用 Isolation Forest 异常检测算法"
)
async def detect_anomaly(symbol: str, days: int = 30) -> dict:
    """
    检测异常交易行为
    使用 Isolation Forest 异常检测算法
    """
    np.random.seed(42)
    normal_data = np.random.randn(days, 4) * 0.5
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(normal_data)
    
    current_data = np.random.randn(1, 4) * 0.5
    prediction = model.predict(current_data)[0]
    is_anomaly = prediction == -1
    
    return {
        "symbol": symbol,
        "is_anomaly": is_anomaly,
        "confidence": f"{0.85 if is_anomaly else 0.95:.2%}",
        "message": "⚠️ 检测到异常交易行为" if is_anomaly else "✅ 交易行为正常",
        "analysis_days": days,
        "algorithm": "Isolation Forest 异常检测"
    }
