# tools/news.py
import random
from datetime import datetime
from . import YA_MCPServer_Tool
from tools import YA_MCPServer_Tool

@YA_MCPServer_Tool(
    name="get_latest_news",
    title="获取最新新闻",
    description="获取标的最新相关新闻"
)
async def get_latest_news(symbol: str, limit: int = 5) -> dict:
    """
    获取标的最新相关新闻
    """
    mock_titles = [
        f"{symbol} 发布季度财报，超出市场预期",
        f"分析师上调 {symbol} 目标价至新高",
        f"行业政策利好，{symbol} 受益明显",
        f"{symbol} 宣布回购计划，提振投资者信心",
        f"市场波动加剧，{symbol} 逆势上涨"
    ]
    
    news_list = []
    for i in range(limit):
        news_list.append({
            "title": mock_titles[i % len(mock_titles)],
            "source": random.choice(["财联社", "彭博社", "Reuters", "新浪财经"]),
            "publish_time": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "url": f"https://example.com/news/{symbol}/{i}",
            "sentiment": random.choice(["positive", "neutral", "negative"])
        })

    return {
        "symbol": symbol,
        "count": len(news_list),
        "news": news_list,
        "update_time": datetime.now().isoformat()
    }

@YA_MCPServer_Tool(
    name="analyze_market_sentiment",
    title="分析市场情感",
    description="分析特定关键词的市场情感倾向"
)
async def analyze_market_sentiment(keyword: str) -> dict:
    """
    分析特定关键词的市场情感倾向
    """
    score = random.uniform(0.4, 0.9)
    
    if score > 0.7:
        level = "非常积极"
        suggestion = "市场情绪高涨，可关注机会"
    elif score > 0.5:
        level = "中性偏多"
        suggestion = "市场情绪平稳，保持观察"
    else:
        level = "消极"
        suggestion = "市场情绪低迷，注意风险"

    return {
        "keyword": keyword,
        "sentiment_score": round(score, 3),
        "sentiment_level": level,
        "suggestion": suggestion,
        "algorithm": "NLP 情感分析 (模拟)",
        "disclaimer": "情感分析基于公开文本，可能存在偏差"
    }
