# 协调器/执行者模式

## 概念

协调器/执行者（Coordinator/Executor）是一种多 Agent 架构模式：

- **协调器（Coordinator）**: 理解用户意图，委托给合适的执行者
- **执行者（Executor）**: 专门处理特定类型的任务

## ADK 实现

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│              root_agent (Coordinator)                        │
│                                                              │
│  • 理解用户意图                                               │
│  • 根据 description 选择合适的 sub_agent                      │
│  • 调用 transfer_to_agent() 委托任务                         │
│  • 整合多个执行者的结果                                       │
│                                                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ↓                  ↓                  ↓
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ time_agent     │  │ calc_agent     │  │ memory_agent   │
│ (Executor)     │  │ (Executor)     │  │ (Executor)     │
│                │  │                │  │                │
│ • get_time     │  │ • calculate    │  │ • remember     │
│ • timezone     │  │ • math ops     │  │ • recall       │
└────────────────┘  └────────────────┘  └────────────────┘
```

### 代码实现

```python
from google.adk.agents import LlmAgent

# 定义执行者 Agent
time_agent = LlmAgent(
    name="time_agent",
    model="gemini-2.0-flash",
    description="Handles time-related queries: current time, timezone conversion.",
    instruction="You are a time specialist. Use your tools to answer time questions.",
    tools=[get_current_time, convert_timezone],
)

calc_agent = LlmAgent(
    name="calc_agent",
    model="gemini-2.0-flash",
    description="Handles mathematical calculations and arithmetic operations.",
    instruction="You are a calculation specialist. Perform math operations.",
    tools=[calculate],
)

# 定义协调器 Agent
root_agent = LlmAgent(
    name="coordinator",
    model="gemini-2.0-flash",
    instruction="Route user requests to the appropriate specialist.",
    sub_agents=[time_agent, calc_agent],  # 注册执行者
)
```

---

## Agent Transfer 机制

### 自动注入的 Prompt

当 Agent 有 `sub_agents` 时，ADK 自动注入 Transfer 指令：

```
You have a list of other agents to transfer to:

Agent name: time_agent
Agent description: Handles time-related queries...

Agent name: calc_agent
Agent description: Handles mathematical calculations...

If another agent is better for answering the question according to its
description, call `transfer_to_agent` function to transfer the question
to that agent.

**NOTE**: the only available agents for `transfer_to_agent` function are
`time_agent`, `calc_agent`.
```

### TransferToAgentTool

```python
# 源码: adk-python/src/google/adk/tools/transfer_to_agent_tool.py

def transfer_to_agent(agent_name: str, tool_context: ToolContext) -> None:
    """Transfer the question to another agent."""
    tool_context.actions.transfer_to_agent = agent_name
```

**关键特性**：
- 自动添加 `enum` 约束，防止 LLM 幻觉不存在的 Agent
- 只能转移到注册的 `sub_agents`

### Transfer 流程

```
User: "What time is it?"
    │
    ↓
Coordinator 收到请求
    │
    ↓
LLM 决策: time_agent 更合适
    │
    ↓
调用 transfer_to_agent("time_agent")
    │
    ↓
time_agent 接管执行
    │
    ↓
time_agent 返回结果
    │
    ↓
Coordinator 返回给用户
```

---

## 父子 Agent 关系

### 访问控制

```python
agent = LlmAgent(
    name="agent",
    sub_agents=[child1, child2],
    disallow_transfer_to_parent=True,  # 禁止转回父 Agent
    disallow_transfer_to_peers=True,   # 禁止转给兄弟 Agent
)
```

### Transfer 目标优先级

```python
# 源码: agent_transfer.py

def _get_transfer_targets(agent: LlmAgent) -> list[BaseAgent]:
    result = []
    result.extend(agent.sub_agents)  # 1. 子 Agent

    if not agent.disallow_transfer_to_parent:
        result.append(agent.parent_agent)  # 2. 父 Agent

    if not agent.disallow_transfer_to_peers:
        result.extend([
            peer_agent
            for peer_agent in agent.parent_agent.sub_agents
            if peer_agent.name != agent.name
        ])  # 3. 兄弟 Agent

    return result
```

---

## 最佳实践

### 1. Description 是关键

```python
# ✅ 好的 description
agent = LlmAgent(
    description="Handles time queries: current time, timezone conversion, scheduling."
)

# ❌ 差的 description
agent = LlmAgent(
    description="A time agent."  # 太模糊，Coordinator 无法判断
)
```

### 2. 避免职责重叠

```python
# ❌ 职责重叠
time_agent = LlmAgent(description="Handles time and date.")
date_agent = LlmAgent(description="Handles date and calendar.")  # 冲突！

# ✅ 职责清晰分离
time_agent = LlmAgent(description="Handles current time and timezone.")
date_agent = LlmAgent(description="Handles calendar events and date arithmetic.")
```

### 3. 使用工厂函数避免重复注册

```python
# ❌ 错误：共享 Agent 实例
shared = LlmAgent(name="shared")
parent1 = LlmAgent(sub_agents=[shared])  # ValidationError!
parent2 = LlmAgent(sub_agents=[shared])

# ✅ 正确：工厂函数
def create_shared():
    return LlmAgent(name="shared")

parent1 = LlmAgent(sub_agents=[create_shared()])
parent2 = LlmAgent(sub_agents=[create_shared()])
```

---

## 实际示例

参见项目源码 `src/adk_cli/agent.py`：

```python
# 协调器
root_agent = LlmAgent(
    name="adk_assistant",
    model="gemini-2.0-flash",
    instruction="...",
    sub_agents=[
        create_time_calc_agent(),
        create_memory_agent(),
        create_task_agent(),
        create_analysis_agent(),
    ],
)
```

---

**Next**: [工具系统](04_tool_system.md)