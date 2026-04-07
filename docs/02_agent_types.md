# Agent 类型与架构

## ADK Agent 类型

ADK 提供四种核心 Agent 类型：

### 1. LlmAgent - LLM 驱动的智能 Agent

```python
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="my_agent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    description="A general-purpose assistant",  # 用于 Agent Transfer
    tools=[tool1, tool2],                       # 工具列表
    sub_agents=[sub_agent1, sub_agent2],        # 子 Agent（协调器模式）
    planner=PlanReActPlanner(),                 # ReAct 模式
    before_agent_callback=...,                  # 回调
    after_agent_callback=...,
)
```

**核心属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | str | Agent 标识符，用于 Transfer |
| `model` | str/BaseLlm | 使用的 LLM 模型 |
| `instruction` | str/Callable | Agent 指令（可动态生成） |
| `description` | str | 描述（用于其他 Agent 选择） |
| `tools` | list[Tool] | 可用工具 |
| `sub_agents` | list[Agent] | 子 Agent |
| `planner` | BasePlanner | 执行规划器 |

### 2. SequentialAgent - 顺序执行

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[
        research_agent,    # 第一步：研究
        analysis_agent,    # 第二步：分析
        summary_agent,     # 第三步：总结
    ],
)
```

**执行流程**：

```
User Input → Agent 1 → Agent 2 → Agent 3 → Final Output
```

### 3. ParallelAgent - 并行执行

```python
from google.adk.agents import ParallelAgent

parallel = ParallelAgent(
    name="parallel",
    sub_agents=[
        weather_agent,     # 并行查询天气
        news_agent,        # 并行查询新闻
        calendar_agent,    # 并行查询日程
    ],
)
```

**执行流程**：

```
         ┌─ Agent 1 ─┐
User ────┼─ Agent 2 ─┼──── Merged Output
         └─ Agent 3 ─┘
```

### 4. LoopAgent - 循环执行

```python
from google.adk.agents import LoopAgent

loop = LoopAgent(
    name="iteration_loop",
    sub_agents=[worker_agent],
    max_iterations=10,  # 最大循环次数
)
```

**执行流程**：

```
┌──────────────────────────────────────┐
│                                      │
│    ┌──────────────┐                  │
│    │ worker_agent │                  │
│    └──────────────┘                  │
│           │                          │
│           ↓                          │
│    [继续/终止判断]                    │
│           │                          │
│    ┌──────┴──────┐                   │
│    │             │                   │
│  继续           终止                  │
│    │             │                   │
│    ↓             └───→ Exit          │
│    └──────────────┘                  │
│                                      │
└──────────────────────────────────────┘
```

---

## Agent 树结构

ADK 使用树状结构组织 Agent：

```python
# 协调器模式
root_agent = LlmAgent(
    name="coordinator",
    model="gemini-2.0-flash",
    instruction="Decide which specialist to use.",
    sub_agents=[
        time_agent,
        calc_agent,
        memory_agent,
    ],
)
```

**树结构**：

```
coordinator (root)
    ├── time_agent (sub)
    ├── calc_agent (sub)
    └── memory_agent (sub)
```

**关键机制**：
- `root_agent` 作为入口
- `sub_agents` 作为执行者
- `transfer_to_agent()` 实现 Agent 间跳转

---

## Agent 生命周期

```python
# 源码: adk-python/src/google/adk/agents/base_agent.py

class BaseAgent:
    async def run_async(self, invocation_context) -> AsyncGenerator[Event]:
        """运行 Agent 的核心方法"""

        # 1. before_agent_callback
        if self.before_agent_callback:
            await self.before_agent_callback(callback_context)

        # 2. 执行 Agent 逻辑
        async for event in self._run_logic(invocation_context):
            yield event

        # 3. after_agent_callback
        if self.after_agent_callback:
            await self.after_agent_callback(callback_context)
```

---

## Agent 配置工厂模式

**重要发现**：ADK Agent 不能被多个父 Agent 共享！

```python
# ❌ 错误做法：共享 Agent 实例
shared_agent = LlmAgent(name="shared")
parent1 = LlmAgent(sub_agents=[shared_agent])  # ValidationError!
parent2 = LlmAgent(sub_agents=[shared_agent])

# ✅ 正确做法：使用工厂函数
def create_shared_agent():
    return LlmAgent(name="shared")

parent1 = LlmAgent(sub_agents=[create_shared_agent()])
parent2 = LlmAgent(sub_agents=[create_shared_agent()])
```

---

## include_contents 配置

控制历史上下文传递：

```python
agent = LlmAgent(
    name="agent",
    include_contents="default",  # 默认：传全部历史
    # include_contents="none",   # 只传当前轮次
)
```

| 值 | 说明 |
|---|------|
| `"default"` | 传递完整对话历史 |
| `"none"` | 只传当前轮次（无历史） |

---

## 子 Agent 访问控制

```python
agent = LlmAgent(
    name="agent",
    disallow_transfer_to_parent=True,  # 禁止转回父 Agent
    disallow_transfer_to_peers=True,   # 禁止转给兄弟 Agent
)
```

---

**Next**: [协调器/执行者模式](03_coordinator_executor.md)