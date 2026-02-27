"""bridge_server.py

一个极简的 Web Bridge：
- 前端：用 Vue3（CDN）做单页，展示输入框 + 闭环过程日志 + 最终答案
- 后端：Starlette + SSE
  - GET /           静态页面
  - GET /app.js     前端逻辑
  - GET /style.css  样式
  - GET /api/chat   SSE：执行 DeepSeek ↔ MCP tools 的闭环，并逐步推送事件

运行方式（需先启动 MCP Server SSE）：
  uv run bridge_server.py

环境变量/ env.yaml：
  DEEPSEEK_API_KEY
  DEEPSEEK_BASE_URL (默认 https://api.deepseek.com/v1)
  DEEPSEEK_MODEL    (默认 deepseek-chat)

说明：
- 该 Bridge 会在服务端持有 DeepSeek API Key，浏览器不会接触密钥。
- SSE 事件 data 为 JSON，每条包含 type 字段，前端按 type 渲染。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import uvicorn
import yaml
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse, StreamingResponse
from starlette.routing import Route

from modules.YA_Common.mcp.mcp_client import MCPClient
from modules.YA_Common.mcp.openai_adapter import OpenAIMCPAdapter
from modules.YA_Common.types.mcp import MCPServerMetadata


DEFAULT_MCP_SERVER_URL = "http://127.0.0.1:19420/"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT_S = 60.0

WEB_DIR = Path(__file__).resolve().parent / "web"


def _load_env_yaml(path: str = "env.yaml") -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
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
    def __init__(self, cfg: DeepSeekConfig, timeout_s: float = DEFAULT_TIMEOUT_S):
        self.cfg = cfg
        self.client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
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
        if resp.status_code // 100 != 2:
            raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text}")
        return resp.json()


def _extract_message(resp_json: Dict[str, Any]) -> Dict[str, Any]:
    choices = resp_json.get("choices") or []
    if not choices:
        return {}
    return choices[0].get("message") or {}


def _extract_tool_calls(msg: Dict[str, Any]) -> List[Dict[str, Any]]:
    tool_calls = msg.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        return tool_calls

    # legacy fallback
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


def _safe_json_loads(s: str) -> Any:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {"_raw": s}


def _sse(obj: Any, event: str | None = None) -> str:
    data = json.dumps(obj, ensure_ascii=False)
    if event:
        return f"event: {event}\ndata: {data}\n\n"
    return f"data: {data}\n\n"


async def _chat_sse(request: Request) -> AsyncGenerator[str, None]:
    params = request.query_params
    query = (params.get("query") or "").strip()
    if not query:
        yield _sse({"type": "error", "message": "缺少 query 参数"})
        return

    server_url = (params.get("server_url") or DEFAULT_MCP_SERVER_URL).strip()
    max_steps = int(params.get("max_steps") or 8)
    verbose = (params.get("verbose") or "0") in {"1", "true", "True"}

    env_yaml = _load_env_yaml("env.yaml")
    api_key = _get_config_value("DEEPSEEK_API_KEY", env_yaml)
    if not api_key:
        yield _sse({"type": "error", "message": "缺少 DEEPSEEK_API_KEY（请设置环境变量或 env.yaml）"})
        return

    base_url = _get_config_value("DEEPSEEK_BASE_URL", env_yaml, DEFAULT_DEEPSEEK_BASE_URL) or DEFAULT_DEEPSEEK_BASE_URL
    model = _get_config_value("DEEPSEEK_MODEL", env_yaml, DEFAULT_DEEPSEEK_MODEL) or DEFAULT_DEEPSEEK_MODEL

    yield _sse(
        {
            "type": "meta",
            "mcp_server_url": server_url,
            "deepseek_base_url": base_url,
            "deepseek_model": model,
            "max_steps": max_steps,
        }
    )

    servers = [MCPServerMetadata(name="mcp_server", url=server_url, transport="sse")]
    adapter = OpenAIMCPAdapter()

    llm = DeepSeekOpenAICompat(DeepSeekConfig(api_key=api_key, base_url=base_url, model=model))

    try:
        async with MCPClient(servers) as mcp:
            yield _sse({"type": "status", "message": "连接 MCP Server 并拉取 tools..."})
            tools = await adapter.create_tools(mcp)
            yield _sse({"type": "tools", "count": len(tools), "tools": tools if verbose else None})

            if not tools:
                yield _sse(
                    {
                        "type": "error",
                        "message": "未获取到任何 MCP tools：请确认 MCP Server（SSE）已启动，且 server_url 指向正确地址。",
                    }
                )
                return

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
                if await request.is_disconnected():
                    return

                req_preview = {
                    "model": model,
                    "messages": messages,
                    "tools_count": len(tools),
                    "tool_choice": "auto",
                }
                yield _sse({"type": "deepseek_request", "step": step, "preview": req_preview if verbose else {"model": model, "tools_count": len(tools)}})

                resp_json = await llm.chat_completions(messages=messages, tools=tools, tool_choice="auto")
                msg = _extract_message(resp_json)
                if not msg:
                    yield _sse({"type": "error", "message": "DeepSeek 返回空 message"})
                    return

                tool_calls = _extract_tool_calls(msg)
                yield _sse({"type": "deepseek_response", "step": step, "message": msg if verbose else {"role": msg.get("role"), "content": msg.get("content"), "tool_calls": tool_calls}})

                if not tool_calls:
                    final_text = (msg.get("content") or "").strip()
                    yield _sse({"type": "final", "content": final_text})
                    return

                messages.append(msg)

                for call in tool_calls:
                    fn = (call.get("function") or {})
                    name = fn.get("name")
                    args_str = fn.get("arguments") or "{}"
                    args = _safe_json_loads(args_str)
                    call_id = call.get("id") or f"call_{step}"

                    yield _sse({"type": "tool_call", "name": name, "arguments": args, "raw_arguments": args_str})

                    executor = adapter.tool_executors.get(name)
                    if executor is None:
                        tool_result: Any = {
                            "error": f"tool executor not found for: {name}",
                            "available": sorted(adapter.tool_executors.keys()),
                        }
                    else:
                        tool_result = await executor(args if isinstance(args, dict) else {})

                    yield _sse({"type": "tool_result", "name": name, "result": tool_result})

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        }
                    )

            yield _sse({"type": "error", "message": f"达到 max_steps={max_steps} 仍未结束（可能进入循环调用）"})

    except Exception as e:
        yield _sse({"type": "error", "message": str(e)})
    finally:
        await llm.aclose()


async def serve_index(_: Request):
    index = WEB_DIR / "index.html"
    if not index.exists():
        return PlainTextResponse("web/index.html not found", status_code=404)
    return FileResponse(index)


async def serve_app_js(_: Request):
    path = WEB_DIR / "app.js"
    if not path.exists():
        return PlainTextResponse("web/app.js not found", status_code=404)
    return FileResponse(path, media_type="text/javascript")


async def serve_style(_: Request):
    path = WEB_DIR / "style.css"
    if not path.exists():
        return PlainTextResponse("web/style.css not found", status_code=404)
    return FileResponse(path, media_type="text/css")


async def api_chat(request: Request):
    return StreamingResponse(
        _chat_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def create_app() -> Starlette:
    app = Starlette(
        routes=[
            Route("/", serve_index),
            Route("/app.js", serve_app_js),
            Route("/style.css", serve_style),
            Route("/api/chat", api_chat),
        ]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("BRIDGE_HOST", "127.0.0.1")
    port = int(os.getenv("BRIDGE_PORT", "19500"))
    uvicorn.run(app, host=host, port=port)
