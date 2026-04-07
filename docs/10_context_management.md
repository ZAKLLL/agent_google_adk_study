# 上下文管理策略

## 默认行为

**ADK 默认传递完整对话历史**。

## 源码分析

```python
# 源码: adk-python/src/google/adk/flows/llm_flows/contents.py

if agent.include_contents == 'default':
    # Include full conversation history  ★ 默认传全部历史
    llm_request.contents = _get_contents(
        invocation_context.branch,
        invocation_context.session.events,  # 所有事件
        agent.name,
    )
```

## 三种控制机制

### 1. include_contents 参数

```python
from google.adk.agents import LlmAgent

# 默认：传全部历史
agent = LlmAgent(
    name="agent",
    include_contents="default",
)

# 只传当前轮次
agent = LlmAgent(
    name="agent",
    include_contents="none",
)
```

| 值 | 说明 |
|---|------|
| `"default"` | 传递完整对话历史（默认） |
| `"none"` | 只传当前轮次，无历史 |

### 2. ContextFilterPlugin

```python
from google.adk.plugins import ContextFilterPlugin

# 保留最近 N 轮对话
filter_plugin = ContextFilterPlugin(
    num_invocations_to_keep=5,
)

agent = LlmAgent(
    plugins=[filter_plugin],
)
```

**Invocation 定义**：一次用户发起的对话（可能包含多轮 model turn + tool calls）

```
Timeline:
  [Invocation 1] User → Model → Tool → Model → Tool → Model
  [Invocation 2] User → Model → Tool → Model
  [Invocation 3] User → Model  ← 当前

num_invocations_to_keep=2 → 只保留 Invocation 2 和 3
```

**源码实现**：

```python
# 源码: adk-python/src/google/adk/plugins/context_filter_plugin.py

async def before_model_callback(self, ..., llm_request):
    contents = llm_request.contents

    # 按 invocation 截断
    invocation_start_indices = _get_invocation_start_indices(contents)
    if len(invocation_start_indices) > self._num_invocations_to_keep:
        split_index = invocation_start_indices[-self._num_invocations_to_keep]

        # 确保 function_call/response 配对
        split_index = _adjust_split_index_to_avoid_orphaned_function_responses(
            contents, split_index
        )

        contents = contents[split_index:]  # ★ 截断
```

**自定义过滤**：

```python
def custom_filter(contents: list[types.Content]) -> list[types.Content]:
    """自定义过滤逻辑"""
    # 按字符数限制
    total_chars = sum(len(c.parts[0].text or "") for c in contents)
    if total_chars > 10000:
        return contents[-5:]  # 只保留最后 5 条
    return contents

filter_plugin = ContextFilterPlugin(custom_filter=custom_filter)
```

### 3. Compaction（历史压缩）

ADK 支持将长历史总结压缩为短摘要：

```python
# 源码: adk-python/src/google/adk/flows/llm_flows/contents.py

def _process_compaction_events(events: list[Event]) -> list[Event]:
    """Processes events by applying compaction.

    Identifies compacted ranges and filters out events that are covered by
    compaction summaries.
    """
    # 压缩后的内容存储在 event.actions.compaction.compacted_content
```

---

## 上下文过滤流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      上下文处理流程                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. 获取 Session Events                                              │
│       ↓                                                              │
│  2. 按分支过滤 (_is_event_belongs_to_branch)                         │
│       ↓                                                              │
│  3. 过滤空事件 (_contains_empty_content)                             │
│       ↓                                                              │
│  4. 过滤 ADK 内部事件 (_is_adk_framework_event)                      │
│       ↓                                                              │
│  5. 应用 Compaction (_process_compaction_events)                    │
│       ↓                                                              │
│  6. ContextFilterPlugin 截断                                         │
│       ↓                                                              │
│  7. 重排 function_call/response 配对                                │
│       ↓                                                              │
│  8. 转换为 LlmRequest.contents                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 事件过滤规则

```python
def _should_include_event_in_context(current_branch, event) -> bool:
    """决定事件是否包含在上下文中"""
    return not (
        _contains_empty_content(event)           # 空内容
        or not _is_event_belongs_to_branch(...)  # 不属于当前分支
        or _is_adk_framework_event(event)        # ADK 内部事件
        or _is_auth_event(event)                 # 认证事件
        or _is_request_confirmation_event(event) # 确认请求事件
    )
```

---

## Token 管理策略

### 问题

LLM 有 token 限制，历史过长会：
1. 超出 context window
2. 增加成本
3. 增加延迟

### 解决方案

| 策略 | 实现方式 | 适用场景 |
|------|----------|----------|
| **截断** | `num_invocations_to_keep` | 简单快速 |
| **压缩** | Compaction | 保留关键信息 |
| **检索** | Memory Service | 超长历史 |

### 最佳实践

```python
from google.adk.agents import LlmAgent
from google.adk.plugins import ContextFilterPlugin

# 生产环境推荐配置
agent = LlmAgent(
    name="agent",
    include_contents="default",
    plugins=[
        ContextFilterPlugin(
            num_invocations_to_keep=10,  # 保留最近 10 轮
            # 或自定义过滤
            # custom_filter=my_filter,
        ),
    ],
)
```

---

## 多 Agent 场景

### 分支隔离

```python
# 不同 Agent 的事件通过 branch 字段隔离

def _is_event_belongs_to_branch(invocation_branch, event) -> bool:
    """检查事件是否属于当前分支"""
    if not invocation_branch or not event.branch:
        return True
    return invocation_branch == event.branch or invocation_branch.startswith(
        f'{event.branch}.'
    )
```

### 其他 Agent 消息处理

```python
def _present_other_agent_message(event: Event) -> Optional[Event]:
    """将其他 Agent 的消息转换为用户上下文"""
    content = types.Content()
    content.role = 'user'
    content.parts = [types.Part(text='For context:')]
    for part in event.content.parts:
        if part.text:
            content.parts.append(
                types.Part(text=f'[{event.author}] said: {part.text}')
            )
    ...
```

---

**Next**: [内置 Prompt 体系](11_builtin_prompts.md)