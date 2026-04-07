# 内置 Prompt 体系

## 概述

ADK 框架会自动注入多个系统级 Prompt，了解这些有助于更好地控制 Agent 行为。

## Prompt 层级结构

```
┌─────────────────────────────────────────────────────────────────────┐
│                 最终发送给 LLM 的 Prompt 层级                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Global Instruction (Plugin)     ← 应用级统一人格                │
│  2. Identity Prompt                 ← 自动：名称 + 描述             │
│  3. Agent Transfer Prompt           ← 自动：子 Agent 列表           │
│  4. ReAct Planner Prompt            ← 使用 Planner 时注入          │
│  5. Agent Instruction               ← 用户定义的 instruction       │
│  6. Conversation History            ← 会话历史                     │
│  7. Tool Declarations               ← 工具声明                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Identity Prompt

**自动注入**，无需配置。

```python
# 源码: adk-python/src/google/adk/flows/llm_flows/identity.py

si = f'You are an agent. Your internal name is "{agent.name}".'
if agent.description:
    si += f' The description about you is "{agent.description}".'
```

**示例输出**：

```
You are an agent. Your internal name is "adk_assistant".
The description about you is "A helpful assistant for ADK demo.".
```

---

## 2. Agent Transfer Prompt

当 Agent 有 `sub_agents` 时自动注入。

```python
# 源码: adk-python/src/google/adk/flows/llm_flows/agent_transfer.py

"""
You have a list of other agents to transfer to:

Agent name: time_agent
Agent description: Handles time-related queries...

Agent name: calc_agent
Agent description: Handles mathematical calculations...

If you are the best to answer the question according to your description,
you can answer it.

If another agent is better for answering the question according to its
description, call `transfer_to_agent` function to transfer the question
to that agent. When transferring, do not generate any text other than
the function call.

**NOTE**: the only available agents for `transfer_to_agent` function are
`time_agent`, `calc_agent`.
"""
```

---

## 3. ReAct Planner Prompt

使用 `PlanReActPlanner()` 时自动注入。

```python
# 源码: adk-python/src/google/adk/planners/plan_re_act_planner.py

# 标签定义
PLANNING_TAG = '/*PLANNING*/'
REPLANNING_TAG = '/*REPLANNING*/'
REASONING_TAG = '/*REASONING*/'
ACTION_TAG = '/*ACTION*/'
FINAL_ANSWER_TAG = '/*FINAL_ANSWER*/'

# Prompt 片段
high_level_preamble = """
When answering the question, try to leverage the available tools...
Follow this process: (1) plan (2) execute (3) final answer
"""

planning_preamble = """
The plan is made to answer the user query...
If the initial plan cannot be successfully executed, revise your plan...
"""

reasoning_preamble = """
The reasoning makes a summary of the current trajectory...
"""

final_answer_preamble = """
The final answer should be precise...
"""
```

---

## 4. State Injection

在 `instruction` 中使用 `{variable}` 语法注入状态。

```python
# 源码: adk-python/src/google/adk/utils/instructions_utils.py

async def inject_session_state(template, readonly_context) -> str:
    """Populates values in the instruction template."""
    # 支持：
    # {state_key}      - 会话级状态
    # {user:key}       - 用户级状态
    # {app:key}        - 应用级状态
    # {artifact.file}  - Artifact 内容
    # {key?}           - 可选（不存在时返回空串）
```

**使用示例**：

```python
agent = LlmAgent(
    instruction="""
    Current user: {user:name}
    Current tasks: {tasks}
    User preferences: {user:preferences?}
    """,
)
```

---

## 5. Global Instruction Plugin

应用级统一指令。

```python
from google.adk.plugins import GlobalInstructionPlugin

plugin = GlobalInstructionPlugin(
    global_instruction="You are a helpful assistant for Company X..."
)
```

**源码**：

```python
# 源码: adk-python/src/google/adk/plugins/global_instruction_plugin.py

async def before_model_callback(self, ..., llm_request):
    existing_instruction = llm_request.config.system_instruction

    if not existing_instruction:
        llm_request.config.system_instruction = final_global_instruction
    else:
        # 拼接在前面
        llm_request.config.system_instruction = (
            f"{final_global_instruction}\n\n{existing_instruction}"
        )
```

---

## 重要发现：无本地化

**ADK 内置 Prompt 全部为英文**，无本地化支持：

```python
# 所有内置 Prompt 都是硬编码英文
"You are an agent..."
"You have a list of other agents..."
"When answering the question..."
```

**解决方案**：在自己的 `instruction` 中明确指定语言：

```python
agent = LlmAgent(
    instruction="请用中文回答用户问题...",  # 用户指令可用中文
    # 但框架注入的 Identity/Transfer/ReAct prompt 仍是英文
)
```

---

## Prompt 组装流程

```python
# 源码: adk-python/src/google/adk/flows/llm_flows/instructions.py

async def _build_instructions(invocation_context, llm_request):
    # 1. Global Instruction (deprecated → use plugin)
    if root_agent.global_instruction:
        llm_request.append_instructions([global_si])

    # 2. Static Instruction
    if agent.static_instruction:
        llm_request.append_instructions(static_content)

    # 3. Dynamic Instruction (状态注入后)
    if agent.instruction:
        si = await _process_agent_instruction(agent, invocation_context)

        if agent.static_instruction:
            # 动态指令作为 user content
            llm_request.contents.append(dynamic_content)
        else:
            # 动态指令作为 system instruction
            llm_request.append_instructions([si])
```

---

## 实际发送示例

假设配置：

```python
root_agent = LlmAgent(
    name="assistant",
    description="Helpful assistant",
    instruction="Help users with their questions.",
    sub_agents=[calc_agent, memory_agent],
    planner=PlanReActPlanner(),
)
```

最终 LLM 收到的 system instruction：

```
[Global Instruction Plugin]
You are a helpful assistant for Company X...

[Identity]
You are an agent. Your internal name is "assistant".
The description about you is "Helpful assistant".

[Agent Transfer]
You have a list of other agents to transfer to:
Agent name: calc_agent
Agent description: Handles calculations...

[ReAct Planner]
When answering the question, try to leverage the available tools...
Follow this process: (1) plan (2) execute (3) final answer...
Use /*PLANNING*/, /*REASONING*/, /*ACTION*/, /*FINAL_ANSWER*/ tags...

[User Instruction]
Help users with their questions.

[Tool Declarations]
- get_current_time(): Returns current time
- calculate(expression): Evaluates math
- transfer_to_agent(agent_name): Transfer to another agent
```

---

## 最佳实践

### 1. 理解 Prompt 优先级

```
Global > Identity > Transfer > ReAct > User Instruction
```

### 2. 避免与内置 Prompt 冲突

```python
# ❌ 可能冲突
agent = LlmAgent(
    instruction="You are a calculator...",  # 与 Identity Prompt 冲突
)

# ✅ 明确任务指令
agent = LlmAgent(
    instruction="Help users perform calculations...",
)
```

### 3. 使用 State Injection 动态化

```python
agent = LlmAgent(
    instruction="""
    User: {user:name}
    Role: {user:role}

    Answer questions based on the user's role.
    """,
)
```

---

**Back to**: [目录](README.md)