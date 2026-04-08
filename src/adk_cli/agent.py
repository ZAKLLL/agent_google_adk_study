"""
Agent definitions demonstrating ADK's multi-agent capabilities.

ADK Agent 系统详解
==================

核心概念：
----------
1. **BaseAgent**: 所有 Agent 的基类
   - 定义了 agent 的基本结构：name, description, sub_agents
   - 提供 run_async() 和 run_live() 方法

2. **LlmAgent**: LLM 驱动的智能代理（最常用）
   - 使用大语言模型进行推理
   - 可以使用工具（tools）
   - 可以有子代理（sub_agents）
   - 支持回调（callbacks）

3. **SequentialAgent**: 顺序执行器
   - 按顺序执行所有 sub_agents
   - 前一个 agent 的输出作为后一个的输入

4. **ParallelAgent**: 并行执行器
   - 同时执行所有 sub_agents
   - 适用于独立的、可并行的任务

=============================================================================
协调器/执行者模式 (Coordinator-Executor Pattern)
=============================================================================

这是 ADK 中最常见的多 agent 架构模式：

┌─────────────────────────────────────────────────────────────────────────┐
│                        Coordinator Agent                                 │
│  (协调器 - 负责理解意图、分解任务、委托执行、整合结果)                      │
│                                                                         │
│  • 理解用户意图                                                          │
│  • 决定委托给哪个执行者                                                   │
│  • 整合多个执行者的结果                                                   │
│  • 处理跨领域的复杂请求                                                   │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┬───────────────┐
            │               │               │               │
            ▼               ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
    │ Executor  │   │ Executor  │   │ Executor  │   │ Executor  │
    │ Agent 1   │   │ Agent 2   │   │ Agent 3   │   │ Agent 4   │
    │ (执行者)   │   │ (执行者)   │   │ (执行者)   │   │ (执行者)   │
    │           │   │           │   │           │   │           │
    │ 时间/计算  │   │ 记忆管理   │   │ 任务管理   │   │ 分析服务   │
    └───────────┘   └───────────┘   └───────────┘   └───────────┘

ADK 实现协调器/执行者模式的关键：
---------------------------------
1. **description 字段**：执行者 agent 的 description 会告诉协调器何时委托
2. **自动路由**：LLM 根据用户请求和 description 自动选择合适的执行者
3. **状态共享**：所有 agent 通过 session state 共享数据
4. **transfer_to_agent**：显式转移控制权的工具

=============================================================================
上下文传递策略 (Context Passing Strategy)
=============================================================================

ADK 中上下文的传递方式：

1. **Session State（会话状态）**
   - 所有 agent 共享同一个 session state
   - 工具通过 ToolContext 访问和修改状态
   - 状态在会话期间持久保存

2. **Instruction 中的占位符**
   - instruction 可以包含 {variable} 占位符
   - 运行时从 state 中注入值
   - 例如: "用户偏好: {user_preferences}"

3. **output_key 字段**
   - LlmAgent 可以设置 output_key
   - agent 的输出会自动存储到 state[output_key]
   - 下一个 agent 可以读取这个值

4. **SequentialAgent 的数据流**
   - 前一个 agent 的输出自动成为后一个 agent 的上下文
   - 通过 output_key 传递结构化数据

=============================================================================
"""

from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.genai import types

from .tools import (
    get_current_time,
    calculate,
    generate_random_number,
    remember_fact,
    recall_facts,
    set_preference,
    get_preference,
    fetch_weather_mock,
    analyze_text,
    add_task,
    list_tasks,
    complete_task,
)
from .callbacks import FULL_CALLBACKS, TOOL_AGENT_CALLBACKS
from .llmmodel import get_executor_model, get_coordinator_model


# ============================================================================
# 执行者 Agent (Executor Agents)
# ==============================
# 这些是专业化的执行者，只处理特定领域的任务
# 关键：description 要清晰描述能力，让协调器知道何时委托
# ============================================================================


def create_time_calc_agent() -> LlmAgent:
    """创建时间计算执行者 Agent。

    执行者 Agent 设计要点：
    ----------------------
    1. **职责单一**: 只处理时间、计算、随机数
    2. **工具专精**: 绑定领域相关的专用工具
    3. **描述精确**: description 决定何时被委托
    4. **温度控制**: 精确任务使用低温度

    Returns:
        配置好的执行者 LlmAgent 实例
    """
    return LlmAgent(
        # 名称：用于日志和调试
        name="time_calc_agent",

        # 模型：通过环境变量配置
        model=get_executor_model(),

        # ★ 关键：描述决定协调器何时委托
        # 协调器 LLM 会读取这个来决定路由
        description="Handles time queries and mathematical calculations.",

        # 指令：定义执行者的行为规范
        # 越具体越好，避免越界处理
        instruction="""
        You are a specialized agent for time and calculation tasks.

        For time queries:
        - Use get_current_time tool with appropriate format if specified
        - Explain the current time clearly

        For calculations:
        - Use calculate tool for mathematical expressions
        - Help users understand the result

        If a task is outside your scope (like remembering facts or managing tasks),
        simply state that and suggest the appropriate agent.
        """,

        # 工具：执行者的"技能"
        tools=[get_current_time, calculate, generate_random_number],

        # 回调：用于日志和监控
        **TOOL_AGENT_CALLBACKS,

        # 生成配置
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3,  # 精确任务用低温度
        ),
    )


def create_memory_agent() -> LlmAgent:
    """创建记忆管理执行者 Agent。

    展示状态操作的执行者模式。

    Returns:
        配置好的执行者 LlmAgent 实例
    """
    return LlmAgent(
        name="memory_agent",
        model=get_executor_model(),
        # ★ 协调器看到这个描述会把记忆相关任务委托过来
        description="Manages stored facts, preferences, and user memory.",
        instruction="""
        You are a memory management specialist.

        Your capabilities:
        - Store facts using remember_fact tool
        - Recall all stored facts using recall_facts tool
        - Set user preferences with set_preference
        - Retrieve preferences with get_preference

        Always confirm what you've stored or retrieved.
        Organize information clearly when presenting stored data.
        """,
        tools=[remember_fact, recall_facts, set_preference, get_preference],
        **TOOL_AGENT_CALLBACKS,
    )


def create_task_agent() -> LlmAgent:
    """创建任务管理执行者 Agent。

    展示 CRUD 操作的执行者模式。

    Returns:
        配置好的执行者 LlmAgent 实例
    """
    return LlmAgent(
        name="task_agent",
        model=get_executor_model(),
        description="Manages user tasks and to-do lists.",
        instruction="""
        You are a task management assistant.

        Your tools:
        - add_task: Add new tasks with priority levels (low/medium/high)
        - list_tasks: Show all tasks with their status
        - complete_task: Mark tasks as done by their ID number

        When adding tasks, ask for priority if not specified (default to medium).
        When listing, show completed and pending tasks clearly.
        """,
        tools=[add_task, list_tasks, complete_task],
        **TOOL_AGENT_CALLBACKS,
    )


def create_analysis_agent() -> LlmAgent:
    """创建分析执行者 Agent。

    展示异步工具和 API 集成的执行者模式。

    Returns:
        配置好的执行者 LlmAgent 实例
    """
    return LlmAgent(
        name="analysis_agent",
        model=get_executor_model(),
        description="Provides weather information and text analysis.",
        instruction="""
        You handle weather queries and text analysis.

        Weather:
        - Use fetch_weather_mock for weather queries (mock data, simulates API delay)
        - Present weather data clearly

        Text Analysis:
        - Use analyze_text to analyze text content
        - Explain the statistics meaningfully

        Note that weather data is simulated for demo purposes.
        """,
        tools=[fetch_weather_mock, analyze_text],
        **TOOL_AGENT_CALLBACKS,
    )


# ============================================================================
# 协调器 Agent (Coordinator Agent)
# ================================
# 协调器负责：理解用户意图、分解任务、委托执行、整合结果
# 关键：sub_agents 列表定义了可用的执行者池
# ============================================================================

root_agent = LlmAgent(
    # 协调器名称
    name="adk_assistant",

    # 协调器通常使用更强的模型
    # 通过环境变量配置，默认使用 glm-4-flash
    model=get_coordinator_model(),

    # 协调器自己的描述（用于更高层级的协调）
    description="A multi-capable assistant orchestrating specialized agents.",

    # ★ 协调器指令：包含执行者信息以便正确委托
    # 关键要素：
    # 1. 列出所有可用的 sub-agents 及其能力
    # 2. 定义委托决策规则
    # 3. 说明自身可处理的任务
    instruction="""
    You are ADK Assistant, an intelligent orchestrator for a multi-agent system.

    Your specialized sub-agents (delegate to them when appropriate):
    - time_calc_agent: Time queries, calculations, random numbers
    - memory_agent: Store/recall facts, manage preferences
    - task_agent: Task and to-do list management
    - analysis_agent: Weather info, text analysis

    Coordination Guidelines:
    1. For single-domain requests, delegate to the appropriate specialist
    2. For multi-domain requests, coordinate multiple agents
    3. Always introduce yourself as "ADK Assistant" on first interaction
    4. Explain which agent(s) you're delegating to

    Direct Capabilities (you can handle these yourself):
    - get_current_time, calculate, generate_random_number
    - remember_fact, recall_facts, set_preference, get_preference
    - fetch_weather_mock, analyze_text
    - add_task, list_tasks, complete_task

    For complex requests involving multiple capabilities, orchestrate
    your sub-agents appropriately.
    """,

    # ★ sub_agents：定义执行者池
    # ADK 会自动处理 agent 间的委托
    # LLM 根据 description 决定何时委托给谁
    sub_agents=[
        create_time_calc_agent(),
        create_memory_agent(),
        create_task_agent(),
        create_analysis_agent(),
    ],

    # 协调器也可以有工具（用于简单请求的直接处理）
    # 避免过度委托，提高效率
    tools=[
        get_current_time,
        calculate,
        generate_random_number,
        remember_fact,
        recall_facts,
        set_preference,
        get_preference,
        fetch_weather_mock,
        analyze_text,
        add_task,
        list_tasks,
        complete_task,
    ],

    # 协调器使用完整回调：便于调试和监控
    **FULL_CALLBACKS,

    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,  # 协调器需要更灵活
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ],
    ),
)


# ============================================================================
# 工作流编排 Agent (Workflow Orchestration)
# =========================================
# SequentialAgent 和 ParallelAgent 实现更复杂的执行模式
# ============================================================================


def create_sequential_workflow() -> SequentialAgent:
    """创建顺序工作流 Agent。

    顺序工作流模式：
    ---------------
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │  Agent A    │ ──▶ │  Agent B    │ ──▶ │  Agent C    │
    │ (处理输入)   │     │ (处理A的输出)│     │ (处理B的输出)│
    └─────────────┘     └─────────────┘     └─────────────┘

    数据传递：
    --------
    - Agent A 的 output_key 存储结果到 state
    - Agent B 从 state 读取 Agent A 的结果
    - 以此类推...

    使用场景：
    ----------
    - 数据处理管道
    - 多步骤审批流程
    - 线性工作流

    Returns:
        SequentialAgent 实例
    """
    return SequentialAgent(
        name="sequential_workflow",
        description="Executes tasks in sequence: memory -> tasks.",
        # 执行顺序：先 memory_agent，后 task_agent
        sub_agents=[create_memory_agent(), create_task_agent()],
    )


def create_parallel_workflow() -> ParallelAgent:
    """创建并行工作流 Agent。

    并行工作流模式：
    ---------------
              ┌─────────────┐
              │   Input     │
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Agent A │ │ Agent B │ │ Agent C │
    │(并行执行)│ │(并行执行)│ │(并行执行)│
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         └───────────┼───────────┘
                     │
              ┌──────▼──────┐
              │ Aggregated  │
              │   Result    │
              └─────────────┘

    使用场景：
    ----------
    - 独立任务的并行处理
    - 多数据源同时获取
    - 性能优化（减少总时间）

    注意：
    -----
    - Agent 之间不应有依赖关系
    - 共享 state 可能导致竞争

    Returns:
        ParallelAgent 实例
    """
    return ParallelAgent(
        name="parallel_analysis",
        description="Runs time and analysis agents concurrently.",
        sub_agents=[create_time_calc_agent(), create_analysis_agent()],
    )


# ============================================================================
# 高级模式：层级协调 (Hierarchical Coordination)
# ==============================================
# 可以构建多层级的协调器/执行者结构
#
#                    ┌───────────────────┐
#                    │  Master           │
#                    │  Coordinator      │
#                    └─────────┬─────────┘
#                              │
#              ┌───────────────┼───────────────┐
#              │               │               │
#              ▼               ▼               ▼
#        ┌───────────┐   ┌───────────┐   ┌───────────┐
#        │ Sub-      │   │ Sub-      │   │ Sub-      │
#        │ Coordinator│   │ Coordinator│   │ Coordinator│
#        └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
#              │               │               │
#        ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
#        │           │   │           │   │           │
#        ▼           ▼   ▼           ▼   ▼           ▼
#    [Executors] [Executors] [Executors]
#
# 这种模式适合大型、复杂的多 agent 系统
# ============================================================================