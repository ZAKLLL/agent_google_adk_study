# ADK CLI Demo

一个展示 **Google ADK (Agent Development Kit)** 核心能力的命令行应用。

## 功能概览

| 功能 | 命令 | 说明 |
|------|------|------|
| 交互式聊天 | `adk-cli chat` | 多轮对话，支持持久化 |
| 单次查询 | `adk-cli ask "..."` | 快速提问 |
| 恢复会话 | `adk-cli resume <id>` | 恢复历史对话 |
| 列出会话 | `adk-cli list-sessions` | 查看所有保存的会话 |
| OTel Tracing | `--trace` | 启用分布式追踪 |

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env，添加 GOOGLE_API_KEY=your-key
```

### 2. 运行

```bash
# 查看帮助
adk-cli --help

# 交互式聊天（自动持久化）
adk-cli chat

# 单次查询
adk-cli ask "What time is it?"

# 查看架构
adk-cli info
```

## 会话持久化

ADK 内置 SQLite 持久化，会话数据保存在 `~/.adk_cli/data/sessions.db`。

```bash
# 开始聊天（默认持久化）
adk-cli chat
# Session saved: session_abc123
# Resume with: adk-cli resume session_abc123

# 查看所有会话
adk-cli list-sessions

# 恢复历史会话
adk-cli resume session_abc123
```

持久化内容包括：
- 会话状态（记忆、偏好）
- 任务列表
- 对话历史

## OpenTelemetry Tracing

ADK 内置完整的 OTel 支持：

```bash
# 启用 tracing（输出到控制台）
adk-cli --trace --console-trace chat

# 发送到 OTLP Collector
adk-cli --trace --otlp-endpoint http://localhost:4318 chat
```

### 本地 Jaeger 集成

```bash
# 启动 Jaeger
docker run -d --name jaeger \
  -p 16686:16686 -p 4318:4318 \
  jaegertracing/all-in-one:latest

# 启用 tracing
adk-cli --trace --otlp-endpoint http://localhost:4318 chat

# 查看 traces: http://localhost:16686
```

### Trace 数据结构

```
Span: invoke_agent (adk_assistant)
  ├── gen_ai.agent.name = "adk_assistant"
  ├── gen_ai.conversation_id = "session_xxx"
  │
  ├── Span: generate_content
  │   ├── gen_ai.request.model = "gemini-2.0-flash"
  │   └── gen_ai.usage.input_tokens = 150
  │
  └── Span: execute_tool
      ├── gen_ai.tool.name = "get_current_time"
      └── gcp.vertex.agent.tool_response = "..."
```

## Agent 架构

```
root_agent (adk_assistant) ─── 协调器
├── time_calc_agent    ─── 时间/计算/随机数
├── memory_agent       ─── 事实记忆/偏好存储
├── task_agent         ─── 任务管理
└── analysis_agent     ─── 天气/文本分析
```

### 协调器/执行者模式

ADK 使用协调器-执行者模式：

```
┌─────────────────────────────────────────┐
│         Coordinator (adk_assistant)      │
│  • 理解用户意图                           │
│  • 委托给合适的执行者                      │
│  • 整合多个执行者的结果                    │
└───────────────────┬─────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌────────┐   ┌────────┐   ┌────────┐
│Executor│   │Executor│   │Executor│
│Agent 1 │   │Agent 2 │   │Agent 3 │
└────────┘   └────────┘   └────────┘
```

## 工具系统

### 工具类型

| 类型 | 示例 | 说明 |
|------|------|------|
| 基础工具 | `get_current_time`, `calculate` | 无状态、同步 |
| 状态工具 | `remember_fact`, `add_task` | 访问 Session State |
| 异步工具 | `fetch_weather_mock` | 支持异步 I/O |

### 定义工具

```python
def my_tool(param: str, tool_context: ToolContext) -> str:
    """工具描述（LLM 会读取）

    Args:
        param: 参数说明
        tool_context: ADK 自动注入

    Returns:
        结果说明
    """
    # 访问状态
    tool_context.state["key"] = value
    return "result"
```

## 回调系统

```python
# Agent 生命周期回调
before_agent_callback(callback_context) -> Optional[Content]
after_agent_callback(callback_context) -> Optional[Content]

# LLM 调用回调
before_model_callback(callback_context, llm_request) -> Optional[LlmResponse]
after_model_callback(callback_context, llm_response) -> Optional[LlmResponse]

# 工具执行回调
before_tool_callback(tool, args, tool_context) -> Optional[dict]
after_tool_callback(tool, args, tool_context, response) -> Optional[dict]
```

## 项目结构

```
src/adk_cli/
├── agent.py       # Agent 定义（协调器/执行者）
├── tools.py       # 12 个自定义工具
├── callbacks.py   # 回调系统
├── cli.py         # CLI 入口
├── tracing.py     # OTel 配置
└── persistence.py # Session 持久化
```

## ADK 核心概念速查

### Session 状态前缀

```python
tool_context.state["key"]           # 会话级
tool_context.state["user:key"]      # 用户级（跨会话）
tool_context.state["app:key"]       # 应用级（跨用户）
```

### Agent 类型

| 类型 | 用途 |
|------|------|
| `LlmAgent` | LLM 驱动的智能代理 |
| `SequentialAgent` | 顺序执行多个 sub-agents |
| `ParallelAgent` | 并行执行多个 sub-agents |

### Runner 创建

```python
# 内存模式（测试）
runner = Runner(
    app_name="my_app",
    agent=agent,
    session_service=InMemorySessionService(),
)

# 持久化模式（生产）
runner = Runner(
    app_name="my_app",
    agent=agent,
    session_service=SqliteSessionService("sessions.db"),
)
```

## 资源链接

- [ADK 官方文档](https://google.github.io/adk-docs/)
- [ADK Python 源码](https://github.com/google/adk-python)
- [ADK 示例](https://github.com/google/adk-samples)
- [OpenTelemetry](https://opentelemetry.io/)

## 许可证

Apache License 2.0