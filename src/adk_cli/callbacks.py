"""
Callback implementations demonstrating ADK's callback system.

ADK 回调系统详解
================

回调系统是 ADK 的核心扩展机制，允许你在 agent 执行的关键节点注入自定义逻辑。

回调类型和执行顺序：
--------------------

1. Agent 级别回调
   ┌────────────────────────────────────────────┐
   │  before_agent_callback                     │
   │      ↓                                     │
   │  [Agent 执行]                               │
   │      ↓                                     │
   │  after_agent_callback                      │
   └────────────────────────────────────────────┘

2. LLM 调用回调（在 Agent 执行内部）
   ┌────────────────────────────────────────────┐
   │  before_model_callback                     │
   │      ↓                                     │
   │  [LLM API 调用]                            │
   │      ↓                                     │
   │  after_model_callback                      │
   └────────────────────────────────────────────┘

3. 工具调用回调（在 LLM 决定使用工具后）
   ┌────────────────────────────────────────────┐
   │  before_tool_callback                      │
   │      ↓                                     │
   │  [工具执行]                                 │
   │      ↓                                     │
   │  after_tool_callback                       │
   └────────────────────────────────────────────┘

回调的关键特性：
----------------
- 可以跳过后续执行（返回 Content/Response 时）
- 可以修改请求/响应
- 可以访问和修改状态
- 可以实现日志、监控、权限控制等横切关注点

类型注解说明：
--------------
- CallbackContext: 提供访问 agent 上下文和状态
- LlmRequest: 发送给 LLM 的请求，可修改
- LlmResponse: LLM 返回的响应，可修改
- BaseTool: 被调用的工具对象
- ToolContext: 工具执行上下文
- types.Content: Gemini API 的内容类型
"""

import logging
from typing import Optional

# ADK 核心类型导入
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Google GenAI 类型
from google.genai import types

logger = logging.getLogger(__name__)


# ============================================================================
# Agent 回调
# ==========
# 在 agent 开始和结束时调用
# 适用于：日志记录、状态初始化、条件检查
# ============================================================================


async def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """Agent 执行前的回调。

    调用时机：
    ---------
    在 Agent.run_async() 开始时，任何其他处理之前。

    使用场景：
    ----------
    1. 日志记录：记录 agent 启动
    2. 状态初始化：设置初始状态值
    3. 条件检查：验证是否应该执行
    4. 性能监控：记录开始时间

    返回值说明：
    ------------
    - None: 继续正常执行 agent
    - types.Content: 跳过 agent 执行，直接返回此内容给用户

    CallbackContext 包含的属性：
    ----------------------------
    - agent_name: 当前 agent 名称
    - invocation_context: 完整的调用上下文
    - state: 可读写的状态字典
    - _event_actions: 用于构建事件动作

    Args:
        callback_context: 包含 agent 上下文和状态访问

    Returns:
        None 继续执行，或 Content 跳过执行
    """
    agent_name = callback_context.agent_name
    logger.info(f"[Callback] Agent '{agent_name}' starting...")

    # 状态操作示例：跟踪调用次数
    # 状态在会话期间持久保存
    invocations = callback_context.state.get("invocation_count", 0)
    callback_context.state["invocation_count"] = invocations + 1

    # 记录会话信息
    session_id = callback_context.invocation_context.session.id
    logger.info(f"[Callback] Session: {session_id}, Invocation #{invocations + 1}")

    # 返回 None 表示继续执行 agent
    # 如果返回 Content，则会跳过 agent 执行
    # 例如：权限检查失败时可以直接返回错误消息
    # if not user_has_permission():
    #     return types.Content(
    #         role="model",
    #         parts=[types.Part(text="Permission denied.")]
    #     )

    return None  # 继续正常执行


async def after_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """Agent 执行后的回调。

    调用时机：
    ---------
    在 Agent 完成所有处理后，包括工具调用和 LLM 响应。

    使用场景：
    ----------
    1. 后处理：修改或增强 agent 输出
    2. 清理操作：释放资源
    3. 日志记录：记录完成状态
    4. 指标收集：记录执行指标

    返回值说明：
    ------------
    - None: 不修改输出
    - types.Content: 追加到 agent 的输出中

    Args:
        callback_context: 包含 agent 上下文

    Returns:
        None 或要追加的内容
    """
    agent_name = callback_context.agent_name
    logger.info(f"[Callback] Agent '{agent_name}' completed.")

    # 可以添加后处理逻辑
    # 例如：总结、格式化、添加元数据

    return None


# ============================================================================
# Model 回调
# ==========
# 在 LLM API 调用前后执行
# 适用于：请求修改、响应过滤、成本监控
# ============================================================================


async def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """LLM 调用前的回调。

    调用时机：
    ---------
    在构造完 LLM 请求后，发送给模型之前。

    LlmRequest 结构：
    -----------------
    - contents: 对话历史 (list[types.Content])
    - tools: 可用工具列表
    - config: 生成配置（温度、token 限制等）
    - system_instruction: 系统指令

    使用场景：
    ----------
    1. 修改请求：添加/修改系统指令、用户消息
    2. 内容过滤：检查敏感内容
    3. 成本控制：检查 token 数量
    4. 请求日志：记录完整请求

    返回值说明：
    ------------
    - None: 继续调用 LLM
    - LlmResponse: 跳过 LLM 调用，使用此响应

    Args:
        callback_context: Agent 上下文
        llm_request: LLM 请求对象，可修改

    Returns:
        None 或模拟的 LLM 响应
    """
    logger.debug(f"[Callback] Before model call")

    # 查看请求内容
    # llm_request.contents 是对话历史
    # 每个 Content 包含 role (user/model) 和 parts
    logger.debug(f"[Callback] Request contents: {len(llm_request.contents)} items")

    # 示例：修改用户消息
    # 注意：这会影响 LLM 看到的内容
    # for content in llm_request.contents:
    #     if content.role == 'user' and content.parts:
    #         for part in content.parts:
    #             if part.text:
    #                 # 添加前缀
    #                 part.text = f"[User Query]: {part.text}"

    # 示例：检查敏感词
    # last_user_message = ...
    # if contains_sensitive_content(last_user_message):
    #     return LlmResponse(
    #         content=types.Content(
    #             role="model",
    #             parts=[types.Part(text="I cannot process that request.")]
    #         )
    #     )

    return None  # 继续调用 LLM


async def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """LLM 调用后的回调。

    调用时机：
    ---------
    在收到 LLM 响应后，处理之前。

    LlmResponse 结构：
    ------------------
    - content: 响应内容 (types.Content)
    - usage_metadata: token 使用量
    - partial: 是否为流式响应的一部分
    - function_calls: 工具调用请求

    使用场景：
    ----------
    1. 响应过滤：移除或修改敏感内容
    2. 内容增强：添加格式化、引用
    3. 成本监控：记录 token 使用
    4. 质量检查：验证响应质量

    Args:
        callback_context: Agent 上下文
        llm_response: LLM 响应对象

    Returns:
        None 使用原响应，或返回修改后的响应
    """
    logger.debug(f"[Callback] After model call")

    # 检查是否为流式响应的部分
    if llm_response.partial:
        logger.debug("[Callback] Partial response received")
        # 流式响应时可以累积内容

    # 可以检查和修改响应内容
    # if llm_response.content and llm_response.content.parts:
    #     for part in llm_response.content.parts:
    #         if part.text:
    #             # 修改响应文本
    #             part.text = part.text.replace("sensitive", "***")

    return None  # 使用原始响应


# ============================================================================
# Tool 回调
# =========
# 在工具执行前后调用
# 适用于：输入验证、输出修改、错误处理、权限控制
# ============================================================================


async def before_tool_callback(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext,
) -> Optional[dict]:
    """工具执行前的回调。

    调用时机：
    ---------
    在 LLM 决定调用工具后，工具实际执行前。

    参数说明：
    ----------
    - tool: 工具对象，包含 name, description 等
    - args: LLM 生成的工具参数字典
    - tool_context: 工具上下文，包含状态访问

    使用场景：
    ----------
    1. 参数验证：检查参数有效性
    2. 权限控制：验证用户是否有权使用工具
    3. 参数修改：规范化或转换参数
    4. 工具替换：根据条件使用不同实现

    返回值说明：
    ------------
    - None: 继续执行工具
    - dict: 跳过工具执行，使用此字典作为结果

    Args:
        tool: 要执行的工具
        args: 工具参数（可修改）
        tool_context: 工具上下文

    Returns:
        None 或替代的工具结果
    """
    tool_name = tool.name
    logger.info(f"[Callback] Tool '{tool_name}' called with args: {args}")

    # 示例：参数验证
    if tool_name == "calculate":
        expression = args.get("expression", "")
        # 检查表达式长度
        if len(expression) > 100:
            return {"error": "Expression too long (max 100 characters)"}

    # 示例：权限控制
    # if tool_name == "dangerous_operation":
    #     if not has_permission(tool_context):
    #         return {"error": "Permission denied for this operation"}

    # 示例：参数规范化
    # if "city" in args:
    #     args["city"] = args["city"].strip().title()

    return None  # 继续执行工具


async def after_tool_callback(
    tool: BaseTool,
    args: dict,
    tool_context: ToolContext,
    tool_response: dict,
) -> Optional[dict]:
    """工具执行后的回调。

    调用时机：
    ---------
    在工具执行完成后，返回结果给 LLM 之前。

    使用场景：
    ----------
    1. 结果修改：格式化或增强输出
    2. 错误处理：转换错误消息
    3. 结果缓存：存储工具结果
    4. 日志记录：记录工具调用历史

    Args:
        tool: 执行的工具
        args: 原始工具参数
        tool_context: 工具上下文
        tool_response: 工具返回的结果

    Returns:
        None 使用原结果，或返回修改后的结果
    """
    tool_name = tool.name
    logger.info(f"[Callback] Tool '{tool_name}' returned: {tool_response}")

    # 示例：添加元数据
    # if isinstance(tool_response, dict):
    #     tool_response["_metadata"] = {
    #         "tool_name": tool_name,
    #         "timestamp": datetime.datetime.now().isoformat(),
    #     }

    # 示例：错误处理
    # if "error" in tool_response:
    #     tool_response["user_message"] = "An error occurred. Please try again."

    return None  # 使用原始响应


# ============================================================================
# 回调组合
# =========
# 将回调组织成可复用的配置字典
# 使用 **dict 语法在 LlmAgent 构造时展开
# ============================================================================

# 协调器 Agent 使用的回调
COORDINATOR_CALLBACKS = {
    "before_agent_callback": before_agent_callback,
    "after_agent_callback": after_agent_callback,
}

# 使用工具的 Agent 的回调
TOOL_AGENT_CALLBACKS = {
    "before_tool_callback": before_tool_callback,
    "after_tool_callback": after_tool_callback,
}

# LLM Agent 的模型回调
MODEL_CALLBACKS = {
    "before_model_callback": before_model_callback,
    "after_model_callback": after_model_callback,
}

# 完整回调集：用于需要完整可观测性的 Agent
# 使用 **FULL_CALLBACKS 在 Agent 定义中展开
FULL_CALLBACKS = {
    **COORDINATOR_CALLBACKS,
    **MODEL_CALLBACKS,
    **TOOL_AGENT_CALLBACKS,
}