"""Крошечный MCP-сервер для тестов: initialize, tools/list, tools/call (эхо и ошибка)."""
import json
import sys

ИНСТРУМЕНТЫ = [
    {"name": "echo", "description": "Возвращает текст", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "fetch", "description": "Читает адрес", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
]
for строка in sys.stdin:
    с = json.loads(строка)
    if "id" not in с:
        continue
    м = с["method"]
    if м == "initialize":
        р = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "fake", "version": "1"}}
    elif м == "tools/list":
        р = {"tools": ИНСТРУМЕНТЫ}
    elif м == "tools/call":
        а = с["params"]["arguments"]
        р = {"content": [{"type": "text", "text": "эхо: " + json.dumps(а, ensure_ascii=False)}], "isError": False}
    else:
        р = {}
    print(json.dumps({"jsonrpc": "2.0", "id": с["id"], "result": р}, ensure_ascii=False), flush=True)
