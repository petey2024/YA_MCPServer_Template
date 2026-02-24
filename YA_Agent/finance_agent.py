"""
金融数据智能体 
封装Alpha Vantage聚合API
"""

import os
import aiohttp
import yaml
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
import logging

class FinanceAgent(BaseAgent):
    """金融数据智能体"""
    
    def __init__(self):
        super().__init__(
            name="finance_agent",
            description="金融数据查询智能体，提供股票、汇率、市场指标等数据"
        )
        
        # 修改：使用更可靠的配置加载方法
        self.api_key = self._load_api_key_from_config()
        if not self.api_key:
            # 改为警告而非立即报错，允许工具注册但使用时检查
            self.logger.warning("API Key未配置，金融工具将返回错误信息")
            
        self.base_url = "https://www.alphavantage.co/query"
        self.session = None
        
        # 中文股票名映射字典
        self.symbol_mapping = {
            "苹果": "AAPL", "特斯拉": "TSLA", "微软": "MSFT", "谷歌": "GOOGL",
            "亚马逊": "AMZN", "英伟达": "NVDA", "脸书": "META", "阿里巴巴": "BABA",
            "腾讯": "0700.HK", "百度": "BIDU", "京东": "JD", "拼多多": "PDD",
            "美团": "3690.HK", "小米": "1810.HK", "茅台": "600519.SS",
            "工商银行": "1398.HK", "建设银行": "0939.HK", "中国平安": "2318.HK"
        }
    
    def _load_api_key_from_config(self) -> str:
        """
        从配置文件加载API Key - 增强版本
        支持多种配置源和环境
        """
        # 1. 首先尝试从系统环境变量获取（最高优先级）
        env_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if env_key and env_key.strip() and env_key != "demo":
            self.logger.info("✓ 从系统环境变量获取API Key")
            return env_key.strip()
        
        # 2. 尝试从env.yaml文件获取
        try:
            # 使用更可靠的路径查找方法
            # 获取当前文件的绝对路径
            current_file = os.path.abspath(__file__)
            # 假设env.yaml在项目根目录（YA_Agent的上级的上级）
            project_root = os.path.dirname(os.path.dirname(current_file))
            config_path = os.path.join(project_root, "env.yaml")
            
            self.logger.info(f"尝试从配置文件加载: {config_path}")
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    yaml_key = config.get("ALPHA_VANTAGE_API_KEY")
                    if yaml_key and yaml_key.strip() and yaml_key != "demo":
                        self.logger.info("✓ 从env.yaml文件获取API Key")
                        return yaml_key.strip()
                    else:
                        self.logger.warning("env.yaml中的API Key为空或为demo")
            else:
                self.logger.warning(f"配置文件不存在: {config_path}")
                
        except Exception as e:
            self.logger.error(f"读取env.yaml失败: {e}")
        
        # 3. 尝试从.env文件获取（如果存在）
        try:
            from dotenv import load_dotenv
            # 查找项目根目录的.env文件
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(current_file))
            env_path = os.path.join(project_root, ".env")
            
            if os.path.exists(env_path):
                load_dotenv(env_path)
                dotenv_key = os.getenv("ALPHA_VANTAGE_API_KEY")
                if dotenv_key and dotenv_key.strip() and dotenv_key != "demo":
                    self.logger.info("✓ 从.env文件获取API Key")
                    return dotenv_key.strip()
        except ImportError:
            self.logger.info("未安装python-dotenv，跳过.env文件加载")
        except Exception as e:
            self.logger.error(f"从.env文件加载失败: {e}")
        
        # 4. 都未找到，返回None
        self.logger.error("未找到有效的API Key配置")
        return None
    
    async def init_session(self):
        """初始化HTTP会话"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def process(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """处理金融查询"""
        self.logger.info(f"处理金融查询: {query}")
        
        # 先验证API Key
        if not self._validate_api_key():
            return {"error": "API Key未配置，请在env.yaml中设置ALPHA_VANTAGE_API_KEY"}
        
        # 解析查询类型
        if "股票" in query or "stock" in query.lower():
            symbol = await self._extract_symbol(query)
            return await self.get_stock_quote(symbol)
        elif "汇率" in query or "exchange" in query.lower():
            currencies = await self._extract_currencies(query)
            return await self.get_exchange_rate(*currencies)
        elif "指标" in query or "indicator" in query.lower():
            return await self.get_market_indicator()
        else:
            return {"error": "无法识别的金融查询类型"}
    
    async def get_stock_quote(self, symbol: str = "AAPL") -> Dict[str, Any]:
        """获取股票报价"""
        self.logger.info(f"=== 开始股票查询: {symbol} ===")
        
        if not self._validate_api_key():
            return {"error": "API Key未配置"}
            
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        self.logger.info(f"API请求参数: {params}")
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                raw_response = await response.text()
                self.logger.info(f"API原始响应: {raw_response}")
                
                data = await response.json()
                return self._format_stock_data(data)
        except Exception as e:
            self.logger.error(f"股票API请求失败: {e}")
            return {"error": f"API请求失败: {str(e)}"}
    
    async def get_exchange_rate(self, from_currency: str = "USD", to_currency: str = "CNY") -> Dict[str, Any]:
        """获取汇率"""
        if not self._validate_api_key():
            return {"error": "API Key未配置"}
            
        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "apikey": self.api_key
        }
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                return self._format_exchange_data(data)
        except Exception as e:
            self.logger.error(f"汇率API请求失败: {e}")
            return {"error": f"API请求失败: {str(e)}"}
    
    async def get_market_indicator(self) -> Dict[str, Any]:
        """获取市场指标"""
        if not self._validate_api_key():
            return {"error": "API Key未配置"}
            
        params = {
            "function": "MARKET_STATUS",
            "apikey": self.api_key
        }
        
        try:
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                return data
        except Exception as e:
            self.logger.error(f"市场指标API请求失败: {e}")
            return {"error": f"API请求失败: {str(e)}"}
    
    # 辅助方法
    def _validate_api_key(self) -> bool:
        """验证API Key是否有效"""
        if not self.api_key or self.api_key == "demo":
            self.logger.error("无效的API Key，请设置有效的ALPHA_VANTAGE_API_KEY")
            return False
        return True
    
    def _format_stock_data(self, data: Dict) -> Dict[str, Any]:
        """格式化股票数据 - 增强错误处理"""
        if "Global Quote" in data:
            quote = data["Global Quote"]
            self.logger.info(f"解析后的股票数据: {quote}")
            
            return {
                "symbol": quote.get("01. symbol"),
                "price": quote.get("05. price"),
                "change": quote.get("09. change"),
                "change_percent": quote.get("10. change percent"),
                "volume": quote.get("06. volume"),
                "timestamp": quote.get("07. latest trading day")
            }
        elif "Error Message" in data:
            error_msg = data["Error Message"]
            self.logger.error(f"API返回错误: {error_msg}")
            return {"error": error_msg}
        elif "Note" in data:
            # API调用频率限制
            note = data["Note"]
            self.logger.warning(f"API限制: {note}")
            return {"error": f"API调用频率限制: {note}"}
        else:
            # 未知响应格式，返回原始数据用于调试
            self.logger.error(f"未知API响应格式: {data}")
            return {"error": "未知API响应格式", "raw_data": data}
    
    def _format_exchange_data(self, data: Dict) -> Dict[str, Any]:
        """格式化汇率数据"""
        if "Realtime Currency Exchange Rate" in data:
            rate_data = data["Realtime Currency Exchange Rate"]
            return {
                "from_currency": rate_data.get("1. From_Currency Code"),
                "to_currency": rate_data.get("3. To_Currency Code"),
                "exchange_rate": rate_data.get("5. Exchange Rate"),
                "bid_price": rate_data.get("8. Bid Price"),
                "ask_price": rate_data.get("9. Ask Price"),
                "timestamp": rate_data.get("6. Last Refreshed")
            }
        elif "Error Message" in data:
            return {"error": data["Error Message"]}
        elif "Note" in data:
            return {"error": "API调用频率限制: " + data["Note"]}
        else:
            return {"error": "未找到汇率数据，未知响应格式"}
    
    async def _extract_symbol(self, query: str) -> str:
        """从查询中提取股票代码 - 增强版本"""
        import re
        
        # 1. 先检查中文名称映射
        for chinese_name, symbol in self.symbol_mapping.items():
            if chinese_name in query:
                self.logger.info(f"映射中文股票名 '{chinese_name}' -> '{symbol}'")
                return symbol
        
        # 2. 尝试提取股票代码
        patterns = [
            r'([A-Z]{1,5}\.[A-Z]+)',  # 如 AAPL.O, 0700.HK
            r'([A-Z]{2,5})',          # 如 AAPL, TSLA
            r'(\d{4,5}\.[A-Z]+)',     # 如 0700.HK
            r'股票\s*([A-Z0-9\.]+)',   # 如 "股票 AAPL"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                symbol = matches[0].upper()
                self.logger.info(f"正则提取股票代码: '{symbol}'")
                return symbol
        
        # 3. 默认返回AAPL
        self.logger.warning(f"无法从查询中提取股票代码，使用默认AAPL: {query}")
        return "AAPL"
    
    async def _extract_currencies(self, query: str) -> tuple:
        """从查询中提取货币对"""
        import re
        pattern = r'(\w{3})\s*[对到]\s*(\w{3})'
        match = re.search(pattern, query)
        if match:
            return match.group(1), match.group(2)
        return "USD", "CNY"  # 默认
    
    async def get_stock_prediction(self, symbol: str, days: int = 5) -> Dict[str, Any]:
        """
        获取股票价格预测
        使用 Amazon Chronos-Bolt 模型
        """
        import datetime
        from core.predictor import FinancialPredictor

        self.logger.info(f"=== 开始股票预测: {symbol}, 预测天数: {days} ===")
        
        if not self._validate_api_key():
            return {"error": "API Key未配置"}
            
        # 1. 获取历史数据 (TIME_SERIES_DAILY)
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "compact"
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                data = await response.json()
                
                # 记录完整的 API 响应以便调试
                self.logger.info(f"历史数据API响应: {data}")

                if "Error Message" in data:
                    return {"error": f"API返回错误: {data['Error Message']}"}
                
                # 处理频率限制与提示信息
                if "Note" in data:
                    return {"error": f"API频率限制或其他提示: {data['Note']}"}
                if "Information" in data:
                    return {"error": f"API返回信息: {data['Information']}"}
                
                time_series = data.get("Time Series (Daily)", {})
                if not time_series:
                    # 如果没有数据，返回完整响应用于排查
                    return {"error": f"未能获取历史数据，API响应内容: {data}"}
                
                # Alpha Vantage 数据是倒序的 (最新日期在前)
                # 我们需要正序的历史数据
                sorted_dates = sorted(time_series.keys())
                historical_prices = [float(time_series[d]["4. close"]) for d in sorted_dates]
                
                if len(historical_prices) < 30:
                    return {"error": f"历史数据不足30天 ({len(historical_prices)}天)，难以准确预测"}

                # 3. 调用预测模型
                try:
                    predictor = FinancialPredictor() 
                    forecast = predictor.predict(
                        context=historical_prices,
                        prediction_length=days,
                        num_samples=20
                    )
                    
                    last_date = sorted_dates[-1]
                    last_price = historical_prices[-1]
                    start_date = datetime.datetime.strptime(last_date, "%Y-%m-%d")
                    future_dates = [(start_date + datetime.timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(days)]
                    
                    median_forecast = forecast["median"]
                    lower_80 = forecast["lower_80"]
                    upper_80 = forecast["upper_80"]
                    
                    forecast_list = []
                    for i, date in enumerate(future_dates):
                        pred = median_forecast[i] if i < len(median_forecast) else 0.0
                        trend = "up" if pred > last_price else "down"
                        forecast_list.append({
                            "date": date,
                            "predicted_price": round(float(pred), 2),
                            "confidence_interval_80": [round(float(lower_80[i]), 2), round(float(upper_80[i]), 2)],
                            "trend": trend
                        })
                        
                    return {
                        "symbol": symbol,
                        "last_updated": last_date,
                        "current_price": last_price,
                        "forecast": forecast_list
                    }
                    
                except ImportError as ie:
                    return {"error": f"预测模块导入失败: {ie}"}
                except Exception as e:
                    self.logger.error(f"模型预测出错: {e}")
                    return {"error": f"预测过程出错: {str(e)}"}
                    
        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            return {"error": f"获取历史数据失败: {str(e)}"}

    async def close(self):
        """清理资源"""
        if self.session:
            await self.session.close()