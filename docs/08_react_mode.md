# ReAct 模式

## 概念

ReAct (Reasoning and Acting) 是一种 Agent 模式：
1. **Reasoning（推理）**: Agent 思考下一步应该做什么
2. **Acting（行动）**: Agent 执行工具调用
3. **循环**: 观察结果后继续推理-行动循环

## ADK ReAct 实现

ADK 提供两种 Planner：

### 1. PlanReActPlanner（显式 ReAct）

```python
from google.adk.agents import LlmAgent
from google.adk.planners import PlanReActPlanner

agent = LlmAgent(
    name="react_agent",
    model="gemini-2.0-flash",
    tools=[tool1, tool2],
    planner=PlanReActPlanner(),  # 启用 ReAct
)
```

**输出格式**：

```
/*PLANNING*/
1. First, I need to get the current time
2. Then check if there are any tasks due

/*REASONING*/
The user wants to know their schedule. I have the time, now I need to check tasks.

/*ACTION*/
get_current_time()

/*REASONING*/
Now I have the time (14:30), I should list today's tasks.

/*ACTION*/
list_tasks(date="today")

/*REASONING*/
I have all the information needed. There are 3 tasks due before 5pm.

/*FINAL_ANSWER*/
It's currently 2:30pm. You have 3 tasks due today before 5pm:
1. Review PR #123
2. Team meeting at 3pm
3. Submit report by 5pm
```

### 2. BuiltInPlanner（Gemini 2.5+ 内置）

```python
from google.adk.planners import BuiltInPlanner
from google.genai import types

agent = LlmAgent(
    name="thinking_agent",
    model="gemini-2.5-pro",  # 需要 Gemini 2.5+
    tools=[tool1, tool2],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,  # 在响应中包含思考过程
        )
    ),
)
```

**特点**：
- 使用模型内置的 thinking 能力
- 思考过程在 `part.thought = True` 的 Part 中
- 更自然，但需要特定模型支持

---

## Planner 对比

```
┌────────────────────┬─────────────────────┬─────────────────────┐
│       特性         │  PlanReActPlanner   │   BuiltInPlanner    │
├────────────────────┼─────────────────────┼─────────────────────┤
│ 模型要求           │  任何模型           │  Gemini 2.5+        │
│ 推理可见性         │  显式标签           │  thoughts 字段      │
│ 控制粒度           │  精细控制           │  模型控制           │
│ 适用场景           │  需要结构化推理     │  通用推理任务       │
│ 性能开销           │  较高               │  中等               │
└────────────────────┴─────────────────────┴─────────────────────┘
```

---

## 内置 ReAct Prompt

`PlanReActPlanner` 自动注入以下系统指令：

```python
# 源码: adk-python/src/google/adk/planners/plan_re_act_planner.py

PLANNING_TAG = '/*PLANNING*/'
REPLANNING_TAG = '/*REPLANNING*/'
REASONING_TAG = '/*REASONING*/'
ACTION_TAG = '/*ACTION*/'
FINAL_ANSWER_TAG = '/*FINAL_ANSWER*/'

high_level_preamble = """
When answering the question, try to leverage the available tools to gather
the information instead of your memorized knowledge.

Follow this process when answering the question:
(1) first come up with a plan in natural language text format;
(2) Then use tools to execute the plan and provide reasoning between tool
code snippets to make a summary of current state and next step.
(3) In the end, return one final answer.
"""

planning_preamble = """
The plan is made to answer the user query if following the plan.
The plan is coherent and covers all aspects of information from user query,
and only involves the tools that are accessible by the agent.
"""
```

---

## ReAct vs 普通 Agent

### 普通 Agent

```
User Query → LLM → [Tool Call] → Response
```

特点：
- 单次决策
- 工具调用是"一次性"的
- 适合简单任务

### ReAct Agent

```
User Query
    ↓
Planning: 制定计划
    ↓
Reasoning: 推理当前状态
    ↓
Action: 执行工具
    ↓
Observation: 观察结果
    ↓
Reasoning: 分析结果，决定下一步
    ↓
[循环直到完成]
    ↓
Final Answer: 最终答案
```

特点：
- 多步推理
- 动态调整策略
- 适合复杂任务

---

## 适用场景

### 适合 ReAct 的场景

- ✅ 多步骤复杂任务
- ✅ 需要规划的任务
- ✅ 需要解释推理过程
- ✅ 不确定最终路径的问题

### 不需要 ReAct 的场景

- ❌ 简单问答
- ❌ 单次工具调用
- ❌ 固定流程任务（用 SequentialAgent）

---

## ReAct 执行流本质

```python
# ReAct 本质是 LLM 级别的循环

while True:
    # 1. 推理（生成 thought）
    thought = await llm.generate(...)

    # 2. 决策
    if thought.is_final_answer:
        break

    # 3. 行动（执行工具）
    tool_result = await execute_tool(thought.action)

    # 4. 观察（将结果加入上下文）
    context.append(tool_result)
```

---

## 哲学：ReAct 作为智能范式

从 AGI 角度看，ReAct 代表了智能的核心特征：

1. **自主规划**: 不依赖预设流程
2. **动态推理**: 根据观察调整策略
3. **自我反思**: 能够评估和改进

```
传统软件 = 工程化（确定性）
ReAct Agent = 智能化（自主性）

未来方向:
强 ReAct Engine + 智能 Context 管理 = AGI Foundation
```

---

## 最佳实践

### 1. 选择合适的模型

```python
# ReAct 需要较强的推理能力
agent = LlmAgent(
    model="gemini-2.0-flash",  # 或更强的模型
    planner=PlanReActPlanner(),
)
```

### 2. 提供清晰的工具描述

```python
# ✅ 好的工具描述
def search_database(query: str, tool_context: ToolContext) -> str:
    """Searches the company database for information.

    Use this tool when you need to find specific records or data.
    Supports SQL-like query syntax.

    Args:
        query: SQL-like search query (e.g., "name:John AND dept:Sales")
    """
    ...
```

### 3. 允许重规划

```python
# ReAct 会自动在计划失败时重规划
# 确保工具返回有意义的错误信息
```

---

**Next**: [执行流程：内部循环机制](09_execution_flow.md)