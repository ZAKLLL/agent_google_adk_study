# 工具系统

## 工具定义

ADK 使用 `FunctionTool` 包装 Python 函数：

```python
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

def get_current_time(tool_context: ToolContext) -> str:
    """Returns the current time.

    Args:
        tool_context: ADK automatically injects this.

    Returns:
        Current time string.
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 创建工具
tool = FunctionTool(func=get_current_time)
```

## 工具类型

### 1. 基础工具（无状态）

```python
def calculate(expression: str, tool_context: ToolContext) -> str:
    """Evaluates a mathematical expression.

    Args:
        expression: Math expression to evaluate.
        tool_context: Auto-injected by ADK.
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"
```

### 2. 状态感知工具

```python
def remember_fact(fact: str, tool_context: ToolContext) -> str:
    """Stores a fact in session state.

    Args:
        fact: The fact to remember.
        tool_context: Provides access to session state.
    """
    # 访问会话状态
    facts = tool_context.state.get("facts", [])
    facts.append(fact)
    tool_context.state["facts"] = facts  # 持久化

    return f"Remembered: {fact}"

def recall_facts(tool_context: ToolContext) -> str:
    """Recalls all stored facts."""
    facts = tool_context.state.get("facts", [])
    return "\n".join(facts) if facts else "No facts remembered."
```

### 3. 异步工具

```python
async def fetch_data(url: str, tool_context: ToolContext) -> str:
    """Fetches data from a URL asynchronously."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

---

## ToolContext

`ToolContext` 是工具与 ADK 框架的桥梁：

```python
class ToolContext:
    # 1. 状态访问
    state: State             # 会话状态字典
    state["key"]             # 会话级状态
    state["user:key"]        # 用户级状态（跨会话）
    state["app:key"]         # 应用级状态（跨用户）

    # 2. Artifact 操作
    def save_artifact(filename, artifact): ...
    def load_artifact(filename): ...

    # 3. Actions 控制
    actions: EventActions
    actions.skip_summarization = True      # 跳过结果总结
    actions.transfer_to_agent = "agent_x"  # 转移到其他 Agent

    # 4. 工具确认（Human-in-the-loop）
    actions.requested_tool_confirmations[id] = ToolConfirmation(...)

    # 5. 函数调用信息
    function_call_id: str    # 当前函数调用 ID
```

### State 前缀约定

```python
# 源码: adk-python/src/google/adk/sessions/state.py

class State:
    APP_PREFIX = "app:"     # 应用级，所有用户共享
    USER_PREFIX = "user:"   # 用户级，跨会话
    TEMP_PREFIX = "temp:"   # 临时，不持久化
```

| 前缀 | 作用域 | 持久化 | 示例 |
|------|--------|--------|------|
| 无 | 会话级 | ✅ | `state["tasks"]` |
| `user:` | 用户级 | ✅ | `state["user:preferences"]` |
| `app:` | 应用级 | ✅ | `state["app:config"]` |
| `temp:` | 临时 | ❌ | `state["temp:cache"]` |

---

## 工具注册

### 直接注册

```python
agent = LlmAgent(
    name="agent",
    tools=[get_current_time, calculate, remember_fact],
)
```

### 使用 Toolset

```python
from google.adk.tools import BaseToolset

class MyToolset(BaseToolset):
    async def get_tools(self, readonly_context) -> list[BaseTool]:
        return [tool1, tool2, tool3]

agent = LlmAgent(tools=[MyToolset()])
```

---

## 工具声明生成

ADK 自动从函数签名生成工具声明：

```python
def calculate(
    expression: str,
    tool_context: ToolContext,
    precision: int = 2,  # 可选参数
) -> str:
    """Evaluates a mathematical expression.

    Args:
        expression: The math expression to evaluate.
        precision: Number of decimal places (default: 2).

    Returns:
        The calculated result as a string.
    """
    ...
```

生成的 FunctionDeclaration：

```json
{
  "name": "calculate",
  "description": "Evaluates a mathematical expression.",
  "parameters": {
    "type": "object",
    "properties": {
      "expression": {"type": "string", "description": "The math expression..."},
      "precision": {"type": "integer", "description": "Number of decimal places..."}
    },
    "required": ["expression"]
  }
}
```

---

## AgentTool - Agent 作为工具

将 Agent 封装为工具，供其他 Agent 调用：

```python
from google.adk.tools import AgentTool

# 子 Agent 作为工具
search_agent = LlmAgent(
    name="search_agent",
    instruction="Perform web searches...",
    tools=[google_search],
)

# 主 Agent 使用子 Agent 作为工具
main_agent = LlmAgent(
    name="main_agent",
    tools=[
        AgentTool(search_agent),  # 封装为工具
        other_tool,
    ],
)
```

---

## 最佳实践

### 1. 文档字符串是关键

```python
# ✅ 好的工具文档
def calculate(expression: str, tool_context: ToolContext) -> str:
    """Evaluates a mathematical expression.

    Supports basic arithmetic: +, -, *, /, **, %.
    Example: "2 + 3 * 4" returns "14".

    Args:
        expression: Valid Python math expression.
        tool_context: Auto-injected by ADK.

    Returns:
        The result as a string, or error message.
    """
    ...

# ❌ 差的工具文档
def calculate(expr, ctx):
    """Calculate something."""
    ...
```

### 2. 错误处理

```python
def risky_operation(param: str, tool_context: ToolContext) -> str:
    """Performs a potentially failing operation."""
    try:
        result = do_something(param)
        return f"Success: {result}"
    except SpecificError as e:
        return f"Failed: {e}. Please try different parameters."
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "An unexpected error occurred. Please try again."
```

### 3. 避免副作用

```python
# ❌ 全局副作用
_global_cache = {}

def save_data(key: str, value: str, tool_context: ToolContext) -> str:
    _global_cache[key] = value  # 问题：多用户冲突
    return "Saved"

# ✅ 使用 State
def save_data(key: str, value: str, tool_context: ToolContext) -> str:
    tool_context.state[f"data:{key}"] = value  # 会话隔离
    return "Saved"
```

---

**Next**: [回调系统](05_callback_system.md)