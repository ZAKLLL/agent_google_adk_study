"""
ReAct Agent 示例

ADK 内置 ReAct 模式
==================

ReAct (Reasoning and Acting) 是一种 agent 模式：
1. **Reasoning（推理）**: Agent 思考下一步应该做什么
2. **Acting（行动）**: Agent 执行工具调用
3. **循环**: 观察结果后继续推理-行动循环

ADK 提供两种 Planner：
-----------------------

1. **PlanReActPlanner** - 显式 ReAct 模式
   ┌─────────────────────────────────────────────────────┐
   │  /*PLANNING*/                                        │
   │  1. First, I need to get the current time           │
   │  2. Then check if there are any tasks due           │
   │                                                      │
   │  /*REASONING*/                                       │
   │  Based on the time, I should prioritize...          │
   │                                                      │
   │  /*ACTION*/                                          │
   │  get_current_time()                                  │
   │                                                      │
   │  /*REASONING*/                                       │
   │  Now I have the time, next I will...                │
   │                                                      │
   │  /*FINAL_ANSWER*/                                    │
   │  Here's your summary...                              │
   └─────────────────────────────────────────────────────┘

2. **BuiltInPlanner** - 模型内置思考（Gemini 2.5+）
   使用模型的 thinking_config 特性

使用方式：
----------
```python
from google.adk.planners import PlanReActPlanner, BuiltInPlanner
from google.genai import types
from .llmmodel import get_react_model, get_thinking_model

# 方式 1: PlanReActPlanner (所有模型适用)
agent = LlmAgent(
    name="react_agent",
    model=get_react_model(),  # 从环境变量读取
    tools=[...],
    planner=PlanReActPlanner(),  # 启用 ReAct
)

# 方式 2: BuiltInPlanner (仅 Gemini 2.5+ 支持)
agent = LlmAgent(
    name="thinking_agent",
    model=get_thinking_model(),  # 需要支持 thinking 的模型
    tools=[...],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,  # 在响应中包含思考过程
        )
    ),
)
```

ReAct vs 普通模式的区别：
------------------------
普通模式：
  User Query → LLM → Tool Call → Response

ReAct 模式：
  User Query → Planning → Reasoning → Action →
  Observation → Reasoning → Action → ... → Final Answer

适用场景：
----------
- 复杂的多步骤任务
- 需要规划的任务
- 需要解释推理过程的场景
"""

from google.adk.agents import LlmAgent
from google.adk.planners import PlanReActPlanner, BuiltInPlanner
from google.genai import types

from .tools import (
    get_current_time,
    calculate,
    generate_random_number,
    remember_fact,
    recall_facts,
    add_task,
    list_tasks,
    fetch_weather_mock,
    analyze_text,
)
from .llmmodel import get_react_model, get_thinking_model


# ============================================================================
# ReAct Agent - 使用 PlanReActPlanner
# ============================================================================
# 显式的 Plan-Reason-Act 循环
# 适合需要清晰推理链的场景

react_agent = LlmAgent(
    name="react_assistant",
    model=get_react_model(),
    description=(
        "A ReAct agent that plans, reasons, and acts step by step. "
        "Use this for complex multi-step tasks requiring planning."
    ),
    instruction="""
    You are a ReAct assistant that follows the Plan-Reason-Act paradigm.

    For complex tasks:
    1. First create a plan
    2. Execute tools step by step
    3. Reason about the results after each step
    4. Provide a final answer

    Use the available tools when needed:
    - Time: get_current_time
    - Math: calculate
    - Memory: remember_fact, recall_facts
    - Tasks: add_task, list_tasks
    - Analysis: fetch_weather_mock, analyze_text
    """,
    tools=[
        get_current_time,
        calculate,
        generate_random_number,
        remember_fact,
        recall_facts,
        add_task,
        list_tasks,
        fetch_weather_mock,
        analyze_text,
    ],
    # ★ 启用 ReAct Planner
    planner=PlanReActPlanner(),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
    ),
)


# ============================================================================
# Thinking Agent - 使用 BuiltInPlanner
# ============================================================================
# 使用 Gemini 2.5+ 的内置思考能力
# 模型会在内部进行推理，思考过程对用户可见

thinking_agent = LlmAgent(
    name="thinking_assistant",
    model=get_thinking_model(),  # 需要 Gemini 2.5+ 或其他支持 thinking 的模型
    description=(
        "A thinking agent that uses Gemini's built-in reasoning. "
        "Shows the thought process before responding."
    ),
    instruction="""
    You are a thoughtful assistant that reasons through problems.

    For each request:
    1. Think through the problem
    2. Consider available tools and information
    3. Provide well-reasoned responses

    Use tools when they help provide better answers.
    """,
    tools=[
        get_current_time,
        calculate,
        remember_fact,
        recall_facts,
        add_task,
        list_tasks,
        fetch_weather_mock,
        analyze_text,
    ],
    # ★ 启用内置思考
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,  # 在响应中包含思考
        )
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
    ),
)


# ============================================================================
# 对比说明
# ============================================================================
"""
两种 Planner 的对比：

┌────────────────────┬─────────────────────┬─────────────────────┐
│       特性         │  PlanReActPlanner   │   BuiltInPlanner    │
├────────────────────┼─────────────────────┼─────────────────────┤
│ 模型要求           │  任何模型           │  Gemini 2.5+        │
│ 推理可见性         │  显式标签           │  thoughts 字段      │
│ 控制粒度           │  精细控制           │  模型控制           │
│ 适用场景           │  需要结构化推理     │  通用推理任务       │
│ 性能开销           │  较高               │  中等               │
└────────────────────┴─────────────────────┴─────────────────────┘

选择建议：
- 需要清晰的推理步骤 → PlanReActPlanner
- 使用 Gemini 2.5+ 且希望简洁 → BuiltInPlanner
- 简单任务不需要推理 → 不使用 planner
"""