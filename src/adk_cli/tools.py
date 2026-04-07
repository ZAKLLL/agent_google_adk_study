"""
Custom tools demonstrating ADK's tool capabilities.

ADK 工具系统核心概念：
=======================

1. **FunctionTool（函数工具）**
   - 最简单的工具定义方式：直接使用 Python 函数
   - ADK 自动解析函数签名、类型提示和 docstring 生成工具 schema
   - 函数的 __name__ 成为工具名称，docstring 成为工具描述

2. **ToolContext（工具上下文）**
   - 每个工具调用时 ADK 自动注入的上下文对象
   - 提供访问 session state 的能力（跨调用持久化数据）
   - 包含 invocation 信息、session ID 等

3. **类型提示的重要性**
   - ADK 使用类型提示生成 LLM 可理解的工具 schema
   - 参数类型、返回类型都会被解析并告诉模型
   - 复杂类型支持：list, dict, Optional, Union 等

工具定义最佳实践：
------------------
1. 函数名使用 snake_case，清晰表达功能
2. 参数名要有意义，类型提示准确
3. docstring 详细描述功能和参数，LLM 会读取这些信息
4. 返回字符串便于 LLM 理解和使用

状态管理策略：
--------------
ADK 的 state 是字典结构，存储在 Session 中：
- 会话级状态：直接使用 key，如 tool_context.state["facts"]
- 用户级状态：使用 "user:" 前缀（跨会话共享）
- 应用级状态：使用 "app:" 前缀（跨用户共享）
"""

import asyncio
import datetime
import json
import random
from typing import Optional

# ToolContext 是 ADK 工具系统的核心类型
# 它提供了访问 session state 和其他上下文信息的能力
from google.adk.tools.tool_context import ToolContext


# ============================================================================
# 基础工具示例
# =============
# 这些工具展示了最简单的 ADK 工具模式：
# - 无状态：不需要访问 session state
# - 同步执行：普通函数
# - 简单类型：str, int 等基础类型
# ============================================================================


def get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取当前时间。

    这是一个最基础的 ADK 工具示例：
    - 函数签名会被 ADK 解析为 JSON Schema
    - 参数的默认值会成为工具的默认参数
    - docstring 会成为 LLM 看到的工具描述

    Args:
        format: 时间格式字符串，默认 "%Y-%m-%d %H:%M:%S"
                LLM 会理解这个参数的用途并正确传值

    Returns:
        格式化的当前时间字符串
    """
    return datetime.datetime.now().strftime(format)


def calculate(expression: str) -> str:
    """安全计算数学表达式。

    这个工具展示了 ADK 工具的错误处理模式：
    - 返回字符串描述结果或错误
    - LLM 可以理解错误信息并重试或调整

    注意：实际生产环境应使用更安全的表达式解析库

    Args:
        expression: 数学表达式，如 "2 + 3 * 4"
                   ADK 会从类型提示知道这是字符串

    Returns:
        计算结果或错误信息
    """
    try:
        # 安全验证：只允许数字和基本运算符
        allowed_chars = set("0123456789+-*/()%. ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"

        # 在受限环境中计算表达式
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"


def generate_random_number(min: int = 1, max: int = 100) -> int:
    """生成指定范围内的随机数。

    这个工具展示了带有多个参数的工具定义：
    - 类型提示帮助 LLM 正确传参
    - 默认值使参数可选

    Args:
        min: 随机数最小值，默认 1
        max: 随机数最大值，默认 100

    Returns:
        生成的随机整数
    """
    return random.randint(min, max)


# ============================================================================
# 状态感知工具示例
# =================
# 这些工具展示了 ADK 的状态管理能力：
# - 通过 ToolContext 访问和修改 session state
# - 状态在会话期间持久保存
# - 可用于实现记忆、偏好等功能
# ============================================================================


def remember_fact(fact: str, tool_context: ToolContext) -> str:
    """记住一个事实，存储在会话状态中。

    这是一个状态感知工具的核心示例：
    -----------------------------
    1. 参数中的 tool_context: ToolContext 是 ADK 的约定
    2. ADK 会自动注入这个参数，LLM 调用时不需要提供
    3. tool_context.state 是一个类似字典的对象

    状态访问模式：
    -------------
    - tool_context.state["key"] = value  # 设置状态
    - tool_context.state.get("key", default)  # 获取状态（安全方式）
    - "key" in tool_context.state  # 检查是否存在

    Args:
        fact: 要记住的事实内容
        tool_context: ADK 自动注入的工具上下文

    Returns:
        确认消息，包含已存储的事实总数
    """
    # 初始化状态中的列表（如果不存在）
    # 注意：需要检查 key 是否存在，避免覆盖已有数据
    if "remembered_facts" not in tool_context.state:
        tool_context.state["remembered_facts"] = []

    # 获取当前列表并添加新事实
    facts = tool_context.state["remembered_facts"]
    facts.append(fact)

    # 更新状态（某些情况下需要显式设置来触发持久化）
    tool_context.state["remembered_facts"] = facts

    return f"Remembered: '{fact}'. Total facts stored: {len(facts)}"


def recall_facts(tool_context: ToolContext) -> str:
    """回忆所有已存储的事实。

    这个工具展示了如何读取状态：
    - 使用 .get() 方法安全获取，避免 KeyError
    - 状态在会话期间持续存在

    Args:
        tool_context: ADK 自动注入的工具上下文

    Returns:
        所有存储的事实列表，或提示无存储
    """
    # 使用 get 方法安全获取，提供默认值
    facts = tool_context.state.get("remembered_facts", [])

    if not facts:
        return "No facts have been stored yet."

    # 格式化输出便于 LLM 理解
    return "Stored facts:\n" + "\n".join(f"- {fact}" for fact in facts)


def set_preference(key: str, value: str, tool_context: ToolContext) -> str:
    """设置用户偏好。

    展示了键值对状态存储模式：
    - 适合存储用户偏好、配置等结构化数据
    - 可以通过不同的 key 存储不同类型的偏好

    Args:
        key: 偏好键名
        value: 偏好值
        tool_context: ADK 工具上下文

    Returns:
        确认消息
    """
    # 获取现有偏好或初始化空字典
    preferences = tool_context.state.get("user_preferences", {})
    preferences[key] = value
    tool_context.state["user_preferences"] = preferences

    return f"Preference set: {key} = {value}"


def get_preference(key: str, tool_context: ToolContext) -> str:
    """获取用户偏好。

    Args:
        key: 偏好键名
        tool_context: ADK 工具上下文

    Returns:
        偏好值或未找到提示
    """
    preferences = tool_context.state.get("user_preferences", {})

    if key not in preferences:
        return f"Preference '{key}' not found."

    return f"Preference '{key}' = {preferences[key]}"


# ============================================================================
# 异步工具示例
# =============
# ADK 完全支持异步工具：
# - 使用 async def 定义
# - 可以执行异步 I/O 操作（API 调用、数据库查询等）
# - LLM 调用时会自动处理 async/await
# ============================================================================


async def fetch_weather_mock(city: str) -> str:
    """模拟获取天气数据（演示异步工具）。

    异步工具的关键点：
    -----------------
    1. 使用 async def 定义函数
    2. 可以使用 await 调用其他异步操作
    3. ADK 会自动处理异步调用

    实际应用中，这里会调用真实的天气 API：
    - 使用 httpx/aiohttp 进行 HTTP 请求
    - 处理 API 响应和错误

    Args:
        city: 城市名称

    Returns:
        模拟的天气数据（JSON 格式）
    """
    # 模拟网络延迟（实际 API 调用会有真实延迟）
    await asyncio.sleep(1)

    # 生成模拟数据
    weather_data = {
        "city": city,
        "temperature": random.randint(15, 35),
        "condition": random.choice(["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]),
        "humidity": random.randint(30, 80),
        "timestamp": datetime.datetime.now().isoformat(),
    }

    # 返回 JSON 字符串便于 LLM 解析
    return json.dumps(weather_data, indent=2)


async def analyze_text(text: str) -> str:
    """分析文本并返回统计信息。

    异步文本分析示例：
    - 可以扩展为调用 NLP API
    - 或使用本地模型进行处理

    Args:
        text: 要分析的文本

    Returns:
        文本统计信息（JSON 格式）
    """
    # 模拟处理延迟
    await asyncio.sleep(0.5)

    words = text.split()
    analysis = {
        "word_count": len(words),
        "character_count": len(text),
        "average_word_length": sum(len(w) for w in words) / len(words) if words else 0,
        "unique_words": len(set(w.lower() for w in words)),
    }

    return json.dumps(analysis, indent=2)


# ============================================================================
# 任务管理工具示例
# =================
# 展示了一个完整的状态管理场景：
# - 复杂的数据结构（字典列表）
# - 增删改查操作
# - 状态更新模式
# ============================================================================


def add_task(task: str, tool_context: ToolContext, priority: str = "medium") -> str:
    """添加任务到任务列表。

    状态管理的复杂示例：
    -------------------
    1. 存储嵌套数据结构（字典的列表）
    2. 每个任务包含多个字段
    3. 使用时间戳记录创建时间

    注意参数顺序：
    -------------
    - 带默认值的参数必须在无默认值参数之后
    - tool_context 是 ADK 注入的，不需要默认值
    - 所以 tool_context 放在 priority 之前

    Args:
        task: 任务描述
        tool_context: ADK 工具上下文
        priority: 优先级 (low/medium/high)，默认 medium

    Returns:
        确认消息，包含任务 ID
    """
    # 初始化任务列表
    if "tasks" not in tool_context.state:
        tool_context.state["tasks"] = []

    tasks = tool_context.state["tasks"]

    # 创建任务对象
    new_task = {
        "id": len(tasks) + 1,
        "task": task,
        "priority": priority,
        "completed": False,
        "created_at": datetime.datetime.now().isoformat(),
    }

    tasks.append(new_task)
    tool_context.state["tasks"] = tasks

    return f"Task added: #{new_task['id']} - '{task}' (priority: {priority})"


def list_tasks(tool_context: ToolContext) -> str:
    """列出所有任务。

    展示如何读取和格式化复杂状态数据。

    Args:
        tool_context: ADK 工具上下文

    Returns:
        任务列表或空提示
    """
    tasks = tool_context.state.get("tasks", [])

    if not tasks:
        return "No tasks in the list."

    # 格式化输出
    result = "Task List:\n"
    for t in tasks:
        # 使用图标表示完成状态
        status = "✓" if t["completed"] else "○"
        result += f"  {status} #{t['id']} [{t['priority']}] {t['task']}\n"

    return result


def complete_task(task_id: int, tool_context: ToolContext) -> str:
    """标记任务为已完成。

    展示如何更新状态中的特定项：
    1. 遍历找到目标
    2. 修改目标属性
    3. 写回整个状态

    Args:
        task_id: 任务 ID
        tool_context: ADK 工具上下文

    Returns:
        确认消息或未找到提示
    """
    tasks = tool_context.state.get("tasks", [])

    for t in tasks:
        if t["id"] == task_id:
            t["completed"] = True
            t["completed_at"] = datetime.datetime.now().isoformat()
            # 写回更新后的状态
            tool_context.state["tasks"] = tasks
            return f"Task #{task_id} completed: '{t['task']}'"

    return f"Task #{task_id} not found."


# ============================================================================
# 工具导出
# =========
# 将所有工具函数放入列表，便于在 Agent 中统一注册
# ADK 会自动将函数转换为 FunctionTool 对象
# ============================================================================

ALL_TOOLS = [
    # 基础工具 - 无状态、同步
    get_current_time,
    calculate,
    generate_random_number,
    # 状态感知工具 - 使用 ToolContext
    remember_fact,
    recall_facts,
    set_preference,
    get_preference,
    # 异步工具 - 使用 async/await
    fetch_weather_mock,
    analyze_text,
    # 任务管理工具 - 复杂状态操作
    add_task,
    list_tasks,
    complete_task,
]