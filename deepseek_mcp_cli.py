"""deepseek_mcp_cli.py

命令行闭环客户端：DeepSeek (LLM) <-> MCP Server tools

目标：
- 连接本项目的 MCP Server (SSE)
- 从 MCP Server 拉取 tools schema
- 调用 DeepSeek Chat Completions（OpenAI 兼容）
- 处理 tool_calls：回调 MCP 工具 -> 将结果以 role=tool 回填 -> 直到得到最终回答
- 在命令行展示完整调用流程（请求/响应/工具调用/最终输出），同时对 API Key 打码

用法示例：
  python deepseek_mcp_cli.py --query "查询 AAPL 最新价格并分析风险"

环境变量（也支持在 env.yaml 中配置同名键）：
  DEEPSEEK_API_KEY
  DEEPSEEK_BASE_URL   (默认 https://api.deepseek.com/v1)
  DEEPSEEK_MODEL      (默认 deepseek-chat)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import yaml

from modules.YA_Common.mcp.mcp_client import MCPClient
from modules.YA_Common.mcp.openai_adapter import OpenAIMCPAdapter
from modules.YA_Common.types.mcp import MCPServerMetadata


DEFAULT_SERVER_URL = "http://127.0.0.1:19420/"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_S = 60.0


def _redact(s: str, keep_last: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= keep_last:
        return "*" * len(s)
    return "*" * (len(s) - keep_last) + s[-keep_last:]


def _load_env_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def _get_config_value(key: str, env_yaml: Dict[str, Any], default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    if v is not None and str(v).strip() != "":
        return str(v).strip()
    if key in env_yaml and str(env_yaml[key]).strip() != "":
        return str(env_yaml[key]).strip()
    return default


@dataclass
class DeepSeekConfig:
    api_key: str
    base_url: str
    model: str


class DeepSeekOpenAICompat:
    """最小 DeepSeek OpenAI-compat client：/chat/completions."""

    def __init__(self, cfg: DeepSeekConfig, timeout_s: float = DEFAULT_TIMEOUT_S):
        self.cfg = cfg
        self.client = httpx.AsyncClient(timeout=timeout_s)

    async def close(self) -> None:
        await self.client.aclose()

    async def chat_completions(
        self,
        *,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        url = f"{self.cfg.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None and tools is not None:
            payload["tool_choice"] = tool_choice

        resp = await self.client.post(url, headers=headers, json=payload)
        # DeepSeek 一般会返回 JSON；非 2xx 直接把 body 打出来方便排查
        if resp.status_code // 100 != 2:
            raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text}")
        return resp.json()


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def _extract_message(resp_json: Dict[str, Any]) -> Dict[str, Any]:
    choices = resp_json.get("choices") or []
    if not choices:
        return {}
    msg = choices[0].get("message") or {}
    return msg


def _extract_tool_calls(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
    # OpenAI 新版：tool_calls
    tool_calls = msg.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        return tool_calls

    # 兼容旧版：function_call
    function_call = msg.get("function_call")
    if isinstance(function_call, dict) and function_call.get("name"):
        return [
            {
                "id": "legacy_function_call",
                "type": "function",
                "function": {
                    "name": function_call.get("name"),
                    "arguments": function_call.get("arguments") or "{}",
                },
            }
        ]

    return []


def _safe_json_loads(s: str) -> Dict[str, Any]:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        # 有些模型会返回非严格 JSON，这里兜底
        return {"_raw": s}


async def run_closed_loop(
    *,
    query: str,
    server_url: str,
    deepseek_cfg: DeepSeekConfig,
    max_steps: int,
    verbose: bool,
) -> str:
    print("=" * 80)
    print("DeepSeek ↔ MCP 闭环客户端启动")
    print(f"MCP Server URL: {server_url}")
    print(f"DeepSeek base_url: {deepseek_cfg.base_url}")
    print(f"DeepSeek model: {deepseek_cfg.model}")
    print(f"DeepSeek api_key: {_redact(deepseek_cfg.api_key)}")
    print("=" * 80)

    servers = [
        MCPServerMetadata(name="mcp_server", url=server_url, transport="sse")
    ]

    adapter = OpenAIMCPAdapter()

    async with MCPClient(servers) as mcp:
        print("[1/5] 连接 MCP Server 并拉取 tools...")
        tools = await adapter.create_tools(mcp)

        print(f"已发现 tools: {len(tools)}")
        if verbose:
            print("tools schema (节选/完整):")
            print(_pretty(tools))

        llm = DeepSeekOpenAICompat(deepseek_cfg)
        try:
            messages: List[Dict[str, Any]] = [
                {
                    "role": "system",
                    "content": (
                        "你是一个金融助手。你可以通过可用工具获取实时数据、新闻、风险评分、异常检测、预测等。"
                        "当需要外部数据时，优先调用工具；拿到工具结果后再给出结论。"
                        "输出请用中文，结构清晰。"
                    ),
                },
                {"role": "user", "content": query},
            ]

            for step in range(1, max_steps + 1):
                print("-" * 80)
                print(f"[2/5] Step {step}: 请求 DeepSeek /chat/completions")

                if verbose:
                    # 打印请求 payload（不含 key）
                    req_preview = {
                        "model": deepseek_cfg.model,
                        "messages": messages,
                        "tools_count": len(tools),
                        "tool_choice": "auto",
                    }
                    print("Request preview:")
                    print(_pretty(req_preview))

                resp_json = await llm.chat_completions(messages=messages, tools=tools, tool_choice="auto")

                if verbose:
                    print("Raw response JSON:")
                    print(_pretty(resp_json))

                msg = _extract_message(resp_json)
                if not msg:
                    raise RuntimeError("DeepSeek 返回空 message，无法继续")

                tool_calls = _extract_tool_calls(msg)

                if not tool_calls:
                    print("[5/5] 模型未发起 tool_calls，闭环结束。")
                    final_text = (msg.get("content") or "").strip()
                    print("最终输出：")
                    print(final_text)
                    return final_text

                # 把 assistant/tool_calls 消息加入历史
                messages.append(msg)

                print(f"[3/5] 模型发起 tool_calls: {len(tool_calls)}")
                for idx, call in enumerate(tool_calls, start=1):
                    fn = (call.get("function") or {})
                    name = fn.get("name")
                    args_str = fn.get("arguments") or "{}"
                    args = _safe_json_loads(args_str)
                    call_id = call.get("id") or f"call_{step}_{idx}"

                    print(f"  - Tool #{idx}: {name}")
                    print(f"    arguments: {args_str}")

                    executor = adapter.tool_executors.get(name)
                    if executor is None:
                        tool_result: Any = {
                            "error": f"tool executor not found for: {name}",
                            "available": sorted(adapter.tool_executors.keys()),
                        }
                    else:
                        print("[4/5] 调用 MCP tool...")
                        tool_result = await executor(args if isinstance(args, dict) else {})

                    if verbose:
                        print("tool_result:")
                        print(_pretty(tool_result))

                    # OpenAI 兼容：role=tool + tool_call_id
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        }
                    )

            raise RuntimeError(f"达到 max_steps={max_steps} 仍未结束。可能是工具输出不足或模型循环调用。")
        finally:
            await llm.close()


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DeepSeek ↔ MCP 闭环命令行客户端")
    p.add_argument("--query", "-q", type=str, default=None, help="一次性问题；不提供则进入交互模式")
    p.add_argument("--server-url", type=str, default=DEFAULT_SERVER_URL, help="MCP Server SSE URL")

    p.add_argument("--deepseek-base-url", type=str, default=None, help="DeepSeek base url (默认从 env/env.yaml 或 https://api.deepseek.com/v1)")
    p.add_argument("--deepseek-model", type=str, default=None, help="DeepSeek model (默认从 env/env.yaml 或 deepseek-chat)")
    p.add_argument("--deepseek-api-key", type=str, default=None, help="直接传入 API Key（不推荐，优先用环境变量/ env.yaml）")

    p.add_argument("--env-yaml", type=str, default="env.yaml", help="env.yaml 路径（用于读取 DEEPSEEK_*）")
    p.add_argument("--max-steps", type=int, default=8, help="最多 tool-calling 循环次数")
    p.add_argument("--verbose", action="store_true", help="打印完整请求/响应 JSON")
    return p


async def _interactive_main(args: argparse.Namespace) -> int:
    env_yaml = _load_env_yaml(args.env_yaml)

    api_key = args.deepseek_api_key or _get_config_value("DEEPSEEK_API_KEY", env_yaml)
    if not api_key:
        print("缺少 DEEPSEEK_API_KEY：请设置环境变量或写入 env.yaml")
        return 2

    base_url = args.deepseek_base_url or _get_config_value(
        "DEEPSEEK_BASE_URL", env_yaml, DEFAULT_DEEPSEEK_BASE_URL
    )
    model = args.deepseek_model or _get_config_value(
        "DEEPSEEK_MODEL", env_yaml, DEFAULT_DEEPSEEK_MODEL
    )

    deepseek_cfg = DeepSeekConfig(api_key=api_key, base_url=base_url, model=model)

    if args.query:
        await run_closed_loop(
            query=args.query,
            server_url=args.server_url,
            deepseek_cfg=deepseek_cfg,
            max_steps=args.max_steps,
            verbose=args.verbose,
        )
        return 0

    # 交互模式
    print("进入交互模式，输入 exit 退出。")
    while True:
        try:
            q = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            return 0
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            print("退出")
            return 0

        try:
            await run_closed_loop(
                query=q,
                server_url=args.server_url,
                deepseek_cfg=deepseek_cfg,
                max_steps=args.max_steps,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"运行失败: {e}")


def main() -> int:
    args = _build_arg_parser().parse_args()
    try:
        return asyncio.run(_interactive_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
