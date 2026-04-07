# 回调系统

## 回调层级

ADK 提供三层回调机制：

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Lifecycle                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  before_agent_callback                               │    │
│  │       ↓                                              │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │           Model Lifecycle                    │    │    │
│  │  │  before_model_callback                       │    │    │
│  │  │       ↓                                      │    │    │
│  │  │  [LLM Call]                                  │    │    │
│  │  │       ↓                                      │    │    │
│  │  │  after_model_callback                        │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │       ↓                                              │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │           Tool Lifecycle                     │    │    │
│  │  │  before_tool_callback                        │    │    │
│  │  │       ↓                                      │    │    │
│  │  │  [Tool Execution]                            │    │    │
│  │  │       ↓                                      │    │    │
│  │  │  after_tool_callback                         │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │       ↓                                              │    │
│  │  after_agent_callback                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent 回调

```python
from google.adk.agents import LlmAgent, CallbackContext
from google.genai import types
from typing import Optional

async def before_agent_callback(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """在 Agent 执行前调用。

    Returns:
        Content: 如果返回内容，则跳过 Agent 执行，直接返回该内容。
        None: 继续正常执行 Agent。
    """
    print(f"Agent {callback_context.agent_name} starting...")

    # 示例：检查前置条件
    if not callback_context.state.get("initialized"):
        return types.Content(
            role="model",
            parts=[types.Part(text="Please initialize first.")],
        )

    return None  # 继续执行

async def after_agent_callback(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """在 Agent 执行后调用。

    Returns:
        Content: 如果返回内容，替换 Agent 的输出。
        None: 使用 Agent 的原始输出。
    """
    print(f"Agent {callback_context.agent_name} completed.")

    # 示例：记录执行
    callback_context.state["last_agent"] = callback_context.agent_name

    return None
```

### 使用方式

```python
agent = LlmAgent(
    name="my_agent",
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)
```

---

## Model 回调

```python
from google.adk.models import LlmRequest, LlmResponse

async def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """在 LLM 调用前调用。

    可以修改请求参数，或短路请求。

    Args:
        callback_context: 回调上下文
        llm_request: 即将发送给 LLM 的请求（可修改）

    Returns:
        LlmResponse: 如果返回响应，跳过 LLM 调用
        None: 继续调用 LLM
    """
    # 示例：修改 temperature
    llm_request.config.temperature = 0.5

    # 示例：添加自定义 header
    llm_request.config.headers["X-Custom"] = "value"

    # 示例：限制输入长度
    total_chars = sum(len(c.parts[0].text or "") for c in llm_request.contents if c.parts)
    if total_chars > 10000:
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Input too long. Please shorten your message.")],
            )
        )

    return None

async def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """在 LLM 响应后调用。

    可以修改或替换响应。

    Args:
        callback_context: 回调上下文
        llm_response: LLM 的响应（可修改）

    Returns:
        LlmResponse: 替换原始响应
        None: 使用原始响应
    """
    # 示例：过滤敏感词
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.text:
                part.text = part.text.replace("secret", "***")

    # 示例：记录 token 使用
    if llm_response.usage_metadata:
        callback_context.state["total_tokens"] = (
            callback_context.state.get("total_tokens", 0) +
            llm_response.usage_metadata.total_token_count
        )

    return None
```

---

## Tool 回调

```python
async def before_tool_callback(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext,
) -> Optional[dict]:
    """在工具执行前调用。

    Args:
        tool: 即将执行的工具
        args: 工具参数
        tool_context: 工具上下文

    Returns:
        dict: 如果返回结果，跳过工具执行，直接返回该结果
        None: 继续执行工具
    """
    # 示例：工具调用限制
    call_count = tool_context.state.get(f"tool_calls:{tool.name}", 0)
    if call_count >= 10:
        return {"error": f"Tool {tool.name} called too many times"}

    # 示例：参数验证/修改
    if tool.name == "delete_file":
        if not args.get("filename", "").startswith("/safe/"):
            return {"error": "Can only delete files in /safe/ directory"}

    # 示例：缓存检查
    cache_key = f"cache:{tool.name}:{hash(frozenset(args.items()))}"
    if cached := tool_context.state.get(cache_key):
        return cached

    return None

async def after_tool_callback(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext,
    response: dict,
) -> Optional[dict]:
    """在工具执行后调用。

    Args:
        tool: 执行的工具
        args: 工具参数
        tool_context: 工具上下文
        response: 工具返回结果

    Returns:
        dict: 替换原始结果
        None: 使用原始结果
    """
    # 示例：缓存结果
    cache_key = f"cache:{tool.name}:{hash(frozenset(args.items()))}"
    tool_context.state[cache_key] = response

    # 示例：记录工具调用
    logs = tool_context.state.get("tool_logs", [])
    logs.append({
        "tool": tool.name,
        "args": args,
        "response": response,
        "timestamp": time.time(),
    })
    tool_context.state["tool_logs"] = logs

    return None
```

---

## 回调注册

### 方式 1：Agent 构造时注册

```python
agent = LlmAgent(
    name="agent",
    before_agent_callback=...,
    after_agent_callback=...,
    before_model_callback=...,
    after_model_callback=...,
    before_tool_callback=...,
    after_tool_callback=...,
)
```

### 方式 2：Plugin 注册

```python
from google.adk.plugins import BasePlugin

class MyPlugin(BasePlugin):
    async def before_model_callback(
        self, *, callback_context, llm_request
    ) -> Optional[LlmResponse]:
        # 所有使用此 Plugin 的 Agent 都会执行
        ...

agent = LlmAgent(
    name="agent",
    plugins=[MyPlugin()],
)
```

---

## CallbackContext

```python
class CallbackContext:
    # 1. Agent 信息
    agent_name: str

    # 2. 状态访问
    state: State

    # 3. 用户信息
    user_id: str

    # 4. 会话信息
    session_id: str

    # 5. 事件操作
    event_actions: EventActions  # 可修改当前事件的 actions
```

---

## 执行顺序

多个回调的执行顺序：

```
1. Plugin callbacks (按 plugins 列表顺序)
2. Agent callbacks

示例：
  plugins=[PluginA, PluginB]

  执行顺序:
    PluginA.before_model_callback
    PluginB.before_model_callback
    Agent.before_model_callback
    [LLM Call]
    Agent.after_model_callback
    PluginB.after_model_callback
    PluginA.after_model_callback
```

---

## 典型用途

| 回调 | 典型用途 |
|------|----------|
| `before_agent` | 前置条件检查、权限验证 |
| `after_agent` | 日志记录、结果后处理 |
| `before_model` | 请求修改、输入限制、缓存检查 |
| `after_model` | 响应过滤、token 统计、内容验证 |
| `before_tool` | 参数验证、调用限制、缓存 |
| `after_tool` | 结果缓存、日志记录、错误处理 |

---

**Next**: [Session 持久化](06_session_persistence.md)