"""
金融数据资源
提供基于真实API的金融数据访问
修复API访问和资源显示问题
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import Resource
import os
import json
import aiohttp
import yaml
from datetime import datetime
from resources import YA_MCPServer_Resource
import logging

logger = logging.getLogger("finance_resources")

# 初始化MCP实例
mcp = FastMCP("FinanceResources")

# 修正：配置正确的Alpha Vantage API基础URL
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

@YA_MCPServer_Resource("finance://market/status")
async def get_market_status() -> str:
    """
    获取真实市场状态信息（从API获取）
    
    Returns:
        市场状态JSON数据
    """
    try:
        # 使用真实API获取市场状态
        params = {
            "function": "MARKET_STATUS"
        }
        
        api_result = await _make_api_request(params)
        
        if "error" in api_result:
            # 如果API失败，返回模拟数据作为降级方案
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "global_markets": {
                    "us_market": "open" if 9 <= datetime.now().hour < 17 else "closed",
                    "hk_market": "open" if 9 <= datetime.now().hour < 16 else "closed",
                    "cn_market": "open" if 9 <= datetime.now().hour < 15 else "closed"
                },
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "使用模拟数据（API调用失败）",
                "api_error": api_result["error"]
            }
        else:
            # 处理真实API响应
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "api_response": api_result,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "alpha_vantage_api"
            }
        
        return json.dumps(status_data, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@YA_MCPServer_Resource("finance://currency/list")
async def get_currency_list() -> str:
    """
    获取支持的货币列表（从API获取实时数据）
    
    Returns:
        货币列表JSON数据
    """
    try:
        # 尝试获取实时汇率数据
        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": "USD",
            "to_currency": "CNY"
        }
        
        api_result = await _make_api_request(params)
        
        if "error" in api_result:
            # 降级到静态数据
            currency_list = [
                {"code": "USD", "name": "美元", "symbol": "$", "status": "static"},
                {"code": "CNY", "name": "人民币", "symbol": "¥", "status": "static"},
                {"code": "EUR", "name": "欧元", "symbol": "€", "status": "static"},
                {"code": "GBP", "name": "英镑", "symbol": "£", "status": "static"},
                {"code": "JPY", "name": "日元", "symbol": "¥", "status": "static"},
                {"code": "HKD", "name": "港币", "symbol": "HK$", "status": "static"},
                {"code": "CAD", "name": "加元", "symbol": "C$", "status": "static"}
            ]
            source = "static_data_fallback"
        else:
            # 处理实时数据
            exchange_data = api_result.get("Realtime Currency Exchange Rate", {})
            currency_list = [
                {
                    "code": "USD", 
                    "name": "美元", 
                    "symbol": "$", 
                    "status": "live",
                    "exchange_rate": exchange_data.get("5. Exchange Rate"),
                    "last_refreshed": exchange_data.get("6. Last Refreshed")
                },
                {
                    "code": "CNY", 
                    "name": "人民币", 
                    "symbol": "¥", 
                    "status": "live",
                    "exchange_rate": "1.0"  # 基准货币
                }
            ]
            source = "alpha_vantage_api"
        
        result = {
            "currencies": currency_list,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@YA_MCPServer_Resource("finance://stock/symbols/{market}")
async def get_stock_symbols(market: str) -> str:
    """
    获取指定市场的股票代码列表（增强版本）
    
    Args:
        market: 市场标识（us, hk, cn, live_us等）
    
    Returns:
        股票代码列表JSON数据
    """
    try:
        # 如果请求实时数据
        if market.lower() == "live_us":
            # 获取美股实时列表
            params = {
                "function": "LISTING_STATUS",
                "state": "active"
            }
            
            api_result = await _make_api_request(params)
            
            if "error" not in api_result:
                # 处理实时股票列表
                live_symbols = []
                stocks_data = api_result.get("data", [])
                for stock in stocks_data[:50]:  # 增加数量限制
                    symbol = stock.get("symbol")
                    if symbol:
                        live_symbols.append(symbol)
                
                return json.dumps({
                    "market": "live_us",
                    "symbols": live_symbols,
                    "count": len(live_symbols),
                    "source": "alpha_vantage_api",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
        
        # 降级到静态数据
        symbol_map = {
            "us": ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "NFLX", "DIS"],
            "hk": ["0700.HK", "0005.HK", "1299.HK", "0941.HK", "0388.HK", "1810.HK"],
            "cn": ["600519.SS", "000001.SZ", "000002.SZ", "601318.SS", "600036.SS"],
            "crypto": ["BTC", "ETH", "ADA", "DOT", "SOL", "BNB", "XRP"],
            "live_us": ["需要有效API Key获取实时数据"]  # 提示信息
        }
        
        symbols = symbol_map.get(market.lower(), [f"未知市场: {market}"])
        return json.dumps({
            "market": market,
            "symbols": symbols,
            "count": len(symbols),
            "source": "static_data",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

@YA_MCPServer_Resource("finance://stock/quote/{symbol}")
async def get_stock_quote_resource(symbol: str) -> str:
    """
    获取股票实时报价（新增资源）
    
    Args:
        symbol: 股票代码
    
    Returns:
        实时股票报价JSON数据
    """
    try:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        
        api_result = await _make_api_request(params)
        
        if "error" in api_result:
            return json.dumps({
                "symbol": symbol,
                "error": api_result["error"],
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 格式化响应
        formatted_result = {
            "symbol": symbol,
            "data": api_result,
            "timestamp": datetime.now().isoformat(),
            "source": "alpha_vantage_api"
        }
        
        return json.dumps(formatted_result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# 导出资源列表
resources = [
    get_market_status, 
    get_currency_list, 
    get_stock_symbols,
    get_stock_quote_resource
]