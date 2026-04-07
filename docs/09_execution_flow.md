# 执行流程：内部循环机制

## 核心发现

**ADK 默认 Agent 不是一问一答模式**，而是内部循环。

## 源码证据

```python
# 源码: adk-python/src/google/adk/flows/llm_flows/base_llm_flow.py

async def run_async(
    self, invocation_context: InvocationContext
) -> AsyncGenerator[Event, None]:
    """Runs the flow."""
    while True:  # ★ 内部有 while 循环！
        last_event = None
        async with Aclosing(self._run_one_step_async(invocation_context)) as agen:
            async for event in agen:
                last_event = event
                yield event

        # 循环退出条件
        if not last_event or last_event.is_final_response() or last_event.partial:
            break
```

## 执行流程图

### 错误理解（一问一答）

```
User Query → LLM → Tool Call → Response (结束)  ❌
```

### 正确理解（内部循环）

```
┌─────────────────────────────────────────────────────────────────────┐
│                       ADK 执行流程                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  while True:                                                         │
│      │                                                               │
│      ├── _run_one_step_async()                                       │
│      │     ├── 调用 LLM (generate_content)                          │
│      │     ├── 如果有 tool_calls → 执行工具 → yield event           │
│      │     └── 如果无 tool_calls → yield final_response             │
│      │                                                               │
│      ├── 检查 last_event.is_final_response()                        │
│      │     ├── True  → break (退出循环)                             │
│      │     └── False → continue (继续下一轮 LLM 调用)               │
│      │                                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## 具体示例

### 用户请求

```
"What time is it and what's my task list?"
```

### 执行过程

```
┌──────────────────────────────────────────────────────────────────┐
│ 第 1 轮循环                                                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  LLM 决策:                                                        │
│    - 需要调用 get_current_time()                                  │
│    - 需要调用 list_tasks()                                        │
│                                                                   │
│  Tool Calls:                                                      │
│    → get_current_time() → "2024-01-15 14:30:00"                  │
│    → list_tasks() → ["Review PR", "Meeting at 3pm"]              │
│                                                                   │
│  is_final_response()? → False (有工具调用，需要继续)              │
│                                                                   │
│  → continue                                                       │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 第 2 轮循环                                                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  LLM 收到:                                                        │
│    - 工具结果: time = "14:30", tasks = [...]                      │
│                                                                   │
│  LLM 决策:                                                        │
│    - 有足够信息，生成最终回答                                      │
│                                                                   │
│  Response:                                                        │
│    "It's 2:30pm. You have 2 tasks: ..."                          │
│                                                                   │
│  is_final_response()? → True (无工具调用)                         │
│                                                                   │
│  → break                                                         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## LoopAgent vs ReAct vs 默认 Agent

| 类型 | 循环层级 | 循环单位 | 终止条件 |
|------|----------|----------|----------|
| **默认 Agent** | LLM 调用级 | 一次 LLM 调用 | `is_final_response()` |
| **ReAct Agent** | 推理级 | 一次思考+行动 | `FINAL_ANSWER` 或无工具调用 |
| **LoopAgent** | Agent 级 | 完整 Agent 执行 | `escalate` 或 `max_iterations` |

### 本质抽象

```python
# 默认 Agent / ReAct Agent（LLM 级循环）
while not is_final_response:
    response = await llm.generate(...)
    if response.tool_calls:
        results = await execute_tools(response.tool_calls)
        context.append(results)
    else:
        return response

# LoopAgent（Agent 级循环）
while iterations < max_iterations and not should_exit:
    for sub_agent in sub_agents:
        await sub_agent.run(session)  # 完整的 Agent 执行
        if event.actions.escalate:
            should_exit = True
```

## 关键方法

### is_final_response()

```python
# 源码: adk-python/src/google/adk/events/event.py

def is_final_response(self) -> bool:
    """Returns True if this event represents a final response."""
    # 无工具调用，且是完整的响应
    return (
        not self.get_function_calls()
        and self.content
        and not self.partial
    )
```

### _run_one_step_async()

```python
async def _run_one_step_async(self, invocation_context) -> AsyncGenerator[Event]:
    """One step means one LLM call."""
    # 1. 预处理
    await self._preprocess_async(invocation_context, llm_request)

    # 2. 调用 LLM
    async for llm_response in self._call_llm_async(...):
        # 3. 后处理（可能执行工具）
        async for event in self._postprocess_async(...):
            yield event
```

---

## 设计意义

ADK 的内部循环设计使得：

1. **开发者无需手动处理循环**：框架自动处理工具调用的多轮交互
2. **统一的执行模型**：无论是否调用工具，代码逻辑一致
3. **自动上下文管理**：工具结果自动注入下一轮 LLM 调用

---

**Next**: [上下文管理策略](10_context_management.md)