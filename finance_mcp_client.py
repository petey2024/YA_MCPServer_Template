# mcp_client_official.py
# 使用官方 MCP SDK 的金融工具客户端 - 优化显示版

import asyncio
import sys
import os
import re
import json
import ast
from datetime import datetime
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# ===================== 配置项 =====================
MCP_SERVER_URL = "http://127.0.0.1:19420/"
SEP_LINE = "=" * 60
BORDER_LINE = "-" * 60

# ===================== 工具函数 =====================
def print_logo():
    print(SEP_LINE)
    print("🎯  MCP 金融工具终端版 (优化显示版) 🎯".center(60))
    print("💹  股票查询 | 汇率转换 | 纯命令行操作  💹".center(60))
    print(SEP_LINE)

def print_success(msg): 
    print(f"\033[32m✅ {msg}\033[0m")

def print_error(msg): 
    print(f"\033[31m❌ {msg}\033[0m")

def print_info(msg): 
    print(f"\033[34mℹ️  {msg}\033[0m")

def print_warning(msg): 
    print(f"\033[33m⚠️  {msg}\033[0m")

def clear_screen(): 
    os.system('cls' if os.name == 'nt' else 'clear')

def format_number(num, decimals=2):
    """格式化数字，添加千分位"""
    try:
        if isinstance(num, str):
            num = float(num)
        if isinstance(num, (int, float)):
            return f"{num:,.{decimals}f}"
        return str(num)
    except:
        return str(num)

def format_percentage(pct):
    """格式化百分比，添加涨跌颜色"""
    try:
        if isinstance(pct, str):
            pct_clean = pct.replace('%', '').replace('+', '').strip()
            pct = float(pct_clean)
        if pct >= 0:
            return f"\033[32m+{pct:.2f}% 📈\033[0m"
        else:
            return f"\033[31m{pct:.2f}% 📉\033[0m"
    except:
        return str(pct)

def extract_text_from_content(result):
    """从 MCP 响应中提取文本内容"""
    text_parts = []
    
    if not result:
        return ""
    
    if hasattr(result, 'content') and result.content:
        for content in result.content:
            if hasattr(content, 'text') and content.text:
                text_parts.append(content.text)
            elif isinstance(content, dict):
                if content.get('type') == 'text' and content.get('text'):
                    text_parts.append(content['text'])
                else:
                    text_parts.append(str(content))
            else:
                text_parts.append(str(content))
    
    if not text_parts:
        text_parts.append(str(result))
    
    return "\n".join(text_parts)

def parse_dict_string(text):
    """尝试将字符串解析为 Python 字典或 JSON"""
    text = text.strip()
    
    # 尝试 JSON 解析
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except:
        pass
    
    # 尝试 Python 字典解析
    try:
        if text.startswith('{') and text.endswith('}'):
            data = ast.literal_eval(text)
            if isinstance(data, dict):
                return data
    except:
        pass
    
    # 尝试从文本中提取字典
    try:
        match = re.search(r'\{[^{}]+\}', text)
        if match:
            dict_str = match.group()
            data = ast.literal_eval(dict_str)
            if isinstance(data, dict):
                return data
    except:
        pass
    
    return None

def display_stock_result(result_text, input_symbol):
    """
    显示股票查询结果
    :param result_text: 服务器返回的原始文本
    :param input_symbol: 用户输入的股票代码
    """
    print("\n" + "📊" * 30)
    print("📈  股 票 行 情  快  报  📈".center(60))
    print("📊" * 30 + "\n")
    
    if not result_text or result_text.strip() == "":
        print_error(f"❌ 服务器返回的数据为空 (股票代码：{input_symbol})")
        print_warning("可能原因：")
        print("   • 股票代码不存在或已退市")
        print("   • 服务器查询失败")
        print("   • 数据源暂时不可用")
        print("\n" + "📊" * 30 + "\n")
        return
    
    print(f"  ⏰ 查询时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(BORDER_LINE)
    
    # 尝试解析为字典
    data = parse_dict_string(result_text)
    
    if data and isinstance(data, dict):
        # 字典格式 - 美化显示
        print("\n📋 股票信息：\n")
        
        # 获取股票名称（如果服务器返回了的话）
        name = data.get('name', data.get('stock_name', data.get('title', '')))
        
        # 获取股票代码（优先使用用户输入的）
        symbol = input_symbol  # 始终显示用户输入的代码
        
        # 显示股票名称和代码
        if name and name.strip():
            print(f"  🏢 股票名称：\033[1;36m{name} ({symbol})\033[0m")
        else:
            # 没有名称，只显示代码
            print(f"  🏢 股票代码：\033[1;36m{symbol}\033[0m")
        
        # 价格信息
        price = data.get('price', data.get('current_price', data.get('latest_price', '')))
        if price:
            print(f"  💰 当前价格：\033[1;33m¥ {format_number(price)}\033[0m")
        
        # 涨跌信息
        change = data.get('change', data.get('change_amount', data.get('price_change', '')))
        change_pct = data.get('change_percent', data.get('change_pct', data.get('percent', '')))
        
        if change_pct:
            print(f"  📊 今日涨跌：{format_percentage(change_pct)}")
        elif change:
            print(f"  📊 今日涨跌：{change}")
        
        print(BORDER_LINE)
        
        # 其他详细信息
        details = [
            ('open', '🌅 今开价格', '¥ '),
            ('high', '📈 最高价格', '¥ '),
            ('low', '📉 最低价格', '¥ '),
            ('volume', '📦 成交量', ''),
            ('amount', '📊 成交额', ''),
            ('market_cap', '💎 总市值', ''),
            ('pe_ratio', '📏 市盈率', ''),
            ('pb_ratio', '📏 市净率', ''),
            ('turnover_rate', '📊 换手率', ''),
            ('amplitude', '📊 振幅', ''),
        ]
        
        for key, label, prefix in details:
            value = data.get(key, '')
            if value:
                print(f"  {label}: {prefix}{value}")
        
        # 时间戳
        timestamp = data.get('timestamp', data.get('time', data.get('update_time', '')))
        if timestamp:
            print(f"  ⏰ 数据时间：{timestamp}")
        
        print(BORDER_LINE)
        
    else:
        # 非字典格式 - 按行显示
        print(f"\n📋 查询结果 ({input_symbol})：\n")
        for line in result_text.strip().split('\n'):
            line = line.strip()
            if line:
                match = re.match(r'^(.+?)[:：]\s*(.+)$', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    if any(k in key.lower() for k in ['价格', 'price']):
                        print(f"  {key}: \033[1;33m{value}\033[0m")
                    elif any(k in key.lower() for k in ['涨跌', 'change', '幅度']):
                        if '+' in value or (value.replace('%', '').replace('.', '').replace('-', '').isdigit() and float(value.replace('%', '')) >= 0):
                            print(f"  {key}: \033[32m{value}\033[0m")
                        else:
                            print(f"  {key}: \033[31m{value}\033[0m")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {line}")
        print(BORDER_LINE)
    
    print("\n" + "📊" * 30)
    print("💡 温馨提示：股市有风险，投资需谨慎！".center(60))
    print("📊" * 30 + "\n")

def display_currency_result(result_text, from_curr, to_curr):
    """
    显示汇率查询结果
    :param result_text: 服务器返回的原始文本
    :param from_curr: 用户输入的原货币
    :param to_curr: 用户输入的目标货币
    """
    print("\n" + "💱" * 30)
    print("💱  实  时  汇  率  查  询  💱".center(60))
    print("💱" * 30 + "\n")
    
    if not result_text or result_text.strip() == "":
        print_error(f"❌ 服务器返回的数据为空 ({from_curr} → {to_curr})")
        print_warning("可能原因：")
        print("   • 货币代码不正确")
        print("   • 服务器查询失败")
        print("   • 数据源暂时不可用")
        print("\n" + "💱" * 30 + "\n")
        return
    
    print(f"  ⏰ 查询时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(BORDER_LINE)
    
    # 尝试解析为字典
    data = parse_dict_string(result_text)
    
    if data and isinstance(data, dict):
        # 字典格式 - 美化显示
        print("\n📋 汇率信息：\n")
        
        # 使用用户输入的货币代码
        print(f"  🌍 货币对：\033[1;36m{from_curr} ➜ {to_curr}\033[0m")
        
        rate = data.get('rate', data.get('exchange_rate', data.get('price', '')))
        if rate:
            rate_num = re.search(r'[\d.]+', str(rate))
            if rate_num:
                rate_formatted = format_number(float(rate_num.group()), 4)
                print(f"  💵 兑换汇率：\033[1;33m1 {from_curr} = {rate_formatted} {to_curr}\033[0m")
            else:
                print(f"  💵 兑换汇率：{rate}")
        
        inverse = data.get('inverse_rate', data.get('inverse', ''))
        if inverse:
            print(f"  🔄 反向汇率：{inverse}")
        
        print(BORDER_LINE)
        
        # 换算示例
        if rate:
            rate_num = re.search(r'[\d.]+', str(rate))
            if rate_num:
                try:
                    rate_val = float(rate_num.group())
                    print("\n💡 换算示例：")
                    print(f"   • 100 {from_curr} ≈ {format_number(100 * rate_val, 2)} {to_curr}")
                    print(f"   • 1,000 {from_curr} ≈ {format_number(1000 * rate_val, 2)} {to_curr}")
                    print(f"   • 10,000 {from_curr} ≈ {format_number(10000 * rate_val, 2)} {to_curr}")
                except:
                    pass
        
        print(BORDER_LINE)
        
    else:
        # 非字典格式 - 按行显示
        print(f"\n📋 查询结果 ({from_curr} → {to_curr})：\n")
        for line in result_text.strip().split('\n'):
            line = line.strip()
            if line:
                match = re.match(r'^(.+?)[:：]\s*(.+)$', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    if any(k in key.lower() for k in ['汇率', 'rate']):
                        print(f"  {key}: \033[1;33m{value}\033[0m")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {line}")
        print(BORDER_LINE)
    
    print("\n" + "💱" * 30)
    print("⚠️  汇率仅供参考，实际交易以银行报价为准  ⚠️".center(60))
    print("💱" * 30 + "\n")

# ===================== MCP 客户端类 =====================
class MCPFinanceClient:
    def __init__(self):
        self.session = None
        self.context = None
        self.connected = False
        
    async def connect(self):
        print_info(f"正在连接服务器：{MCP_SERVER_URL}")
        try:
            self.context = sse_client(MCP_SERVER_URL)
            self._streams = await self.context.__aenter__()
            read_stream, write_stream = self._streams
            
            self.session = ClientSession(read_stream, write_stream)
            await self.session.__aenter__()
            await self.session.initialize()
            
            self.connected = True
            print_success("成功连接到 MCP 服务器！")
            return True
        except Exception as e:
            print_error(f"连接失败：{str(e)}")
            return False
    
    async def disconnect(self):
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            if self.context:
                await self.context.__aexit__(None, None, None)
            self.connected = False
            print_info("已断开连接")
        except Exception as e:
            print_error(f"断开连接时出错：{str(e)}")
    
    async def list_tools(self):
        if not self.connected:
            return None
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            print_error(f"获取工具列表失败：{str(e)}")
            return None
    
    async def call_tool(self, tool_name, arguments):
        if not self.connected:
            return None
        try:
            print_info(f"正在调用：{tool_name}")
            response = await self.session.call_tool(tool_name, arguments)
            return response
        except Exception as e:
            print_error(f"工具调用失败：{str(e)}")
            return None

# ===================== 业务功能 =====================
async def init_session(client):
    print_info("正在获取工具列表...")
    tools = await client.list_tools()
    if tools:
        print_success("会话初始化成功！")
        print_info("📋 可用工具：")
        print(BORDER_LINE)
        for idx, tool in enumerate(tools, 1):
            icon = "📈" if "stock" in tool.name.lower() else "💱" if "currency" in tool.name.lower() else "🔧"
            print(f"   {idx}. {icon} {tool.name}")
        print(BORDER_LINE)
        return True
    return True

async def call_stock(client):
    clear_screen()
    print_logo()
    print_info("📈 股票信息查询")
    print(BORDER_LINE)
    symbol = input("请输入股票代码 (AAPL/600519/MSFT): ").strip()
    if not symbol:
        print_error("股票代码不能为空！")
        input("\n按回车返回...")
        return
    
    print_info(f"正在查询 {symbol} 的股票数据，请稍候...")
    result = await client.call_tool("get_stock_info", {"symbol": symbol})
    
    if result:
        result_text = extract_text_from_content(result)
        # 传递用户输入的 symbol 到显示函数
        display_stock_result(result_text, symbol)
    else:
        print_error(f"❌ 未收到服务器响应 (股票代码：{symbol})")
    
    input("\n按回车返回菜单...")

async def call_currency(client):
    clear_screen()
    print_logo()
    print_info("💱 实时汇率查询")
    print(BORDER_LINE)
    from_curr = input("请输入原货币代码 (CNY/USD/EUR): ").strip().upper()
    to_curr = input("请输入目标货币代码 (USD/EUR/JPY): ").strip().upper()
    if not from_curr or not to_curr:
        print_error("货币代码不能为空！")
        input("\n按回车返回...")
        return
    
    print_info(f"正在查询 {from_curr} → {to_curr} 的汇率，请稍候...")
    result = await client.call_tool("get_currency_rate", {
        "from_currency": from_curr,
        "to_currency": to_curr
    })
    
    if result:
        result_text = extract_text_from_content(result)
        # 传递用户输入的货币代码到显示函数
        display_currency_result(result_text, from_curr, to_curr)
    else:
        print_error(f"❌ 未收到服务器响应 ({from_curr} → {to_curr})")
    
    input("\n按回车返回菜单...")

def print_menu():
    clear_screen()
    print_logo()
    print("🔧  功能菜单（请输入数字选择）  🔧".center(60))
    print(BORDER_LINE)
    print("   1. 📈 查询股票实时信息")
    print("   2. 💱 查询实时汇率转换")
    print("   3. 🔄 重新连接服务器")
    print("   4. 🚪 退出工具")
    print(BORDER_LINE)
    
    while True:
        choice = input("请输入你的选择（1-4）：").strip()
        if choice in ["1", "2", "3", "4"]:
            return choice
        else:
            print_error("输入无效！请输入 1-4 之间的数字")

# ===================== 主程序 =====================
async def main_async():
    clear_screen()
    print_logo()
    print_warning("请确保 MCP Server 已启动：http://127.0.0.1:19420")
    input("\n按回车键开始连接服务器...")
    
    client = MCPFinanceClient()
    
    if not await client.connect():
        print_error("无法连接到服务器，程序退出")
        input("\n按回车键退出...")
        return
    
    await init_session(client)
    input("\n按回车键进入菜单...")
    
    while True:
        choice = print_menu()
        
        if choice == "1":
            await call_stock(client)
        elif choice == "2":
            await call_currency(client)
        elif choice == "3":
            clear_screen()
            print_logo()
            print_info("正在重新连接...")
            await client.disconnect()
            await asyncio.sleep(1)
            if await client.connect():
                await init_session(client)
            input("\n按回车键返回菜单...")
        elif choice == "4":
            await client.disconnect()
            clear_screen()
            print_logo()
            print_success("感谢使用 MCP 金融工具！")
            print_info("🔚 程序已安全退出")
            print(SEP_LINE)
            return

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        clear_screen()
        print_logo()
        print_warning("你已手动中断程序")
        print_success("程序已安全退出")
        print(SEP_LINE)
    except Exception as e:
        print_error(f"程序运行出错：{str(e)}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")

if __name__ == "__main__":
    main()