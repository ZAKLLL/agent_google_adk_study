"""
LLM Model Configuration Module

集中管理所有 Agent 的模型配置，通过环境变量统一配置。

环境变量：
----------
ADK_DEFAULT_MODEL: 默认使用的模型，所有 agent 默认使用此模型
ADK_COORDINATOR_MODEL: 协调器使用的模型（通常需要更强的推理能力）
ADK_EXECUTOR_MODEL: 执行者 agent 使用的模型
ADK_REACT_MODEL: ReAct agent 使用的模型
ADK_THINKING_MODEL: 思考 agent 使用的模型（需要支持 thinking 的 Gemini 2.5+）

优先级：
--------
1. 专用环境变量（如 ADK_COORDINATOR_MODEL）
2. 默认环境变量（ADK_DEFAULT_MODEL）
3. 代码中的硬编码默认值
"""

import os
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """模型配置数据类"""

    name: str
    description: str


# 默认模型配置（当环境变量未设置时使用）
# 使用 OpenRouter 格式: openai/model-name (因为 ADK 使用 LiteLLM)
DEFAULT_MODEL = "openai/qwen/qwen3.6-plus"  # 默认使用 Qwen 3.6 Plus

# OpenRouter 模型示例（通过 LiteLLM/OpenAI 兼容 API）：
# - openai/qwen/qwen3-32b
# - openai/qwen/qwen3-235b-a22b
# - openai/qwen/qwen-2.5-7b-instruct
# - openai/qwen/qwen-2-7b-instruct:free
# - openai/meta-llama/llama-3-8b-instruct:free
# - openai/mistral/mistral-7b-instruct:free
#
# 其他模型：
# - openai/glm-4-flash
# - openai/gpt-3.5-turbo
# - gemini-2.0-flash
# - gemini-2.5-flash


def get_default_model() -> str:
    """
    获取默认模型配置。

    Returns:
        模型名称字符串
    """
    return os.getenv("ADK_DEFAULT_MODEL", DEFAULT_MODEL)


def get_coordinator_model() -> str:
    """
    获取协调器模型配置。
    协调器通常需要更强的推理能力来理解意图和分配任务。

    Returns:
        模型名称字符串
    """
    return os.getenv("ADK_COORDINATOR_MODEL", os.getenv("ADK_DEFAULT_MODEL", DEFAULT_MODEL))


def get_executor_model() -> str:
    """
    获取执行者 agent 模型配置。
    执行者处理特定领域的任务，可以使用较轻量的模型。

    Returns:
        模型名称字符串
    """
    return os.getenv("ADK_EXECUTOR_MODEL", os.getenv("ADK_DEFAULT_MODEL", DEFAULT_MODEL))


def get_react_model() -> str:
    """
    获取 ReAct agent 模型配置。
    ReAct agent 需要推理能力来进行 Plan-Reason-Act 循环。

    Returns:
        模型名称字符串
    """
    return os.getenv("ADK_REACT_MODEL", os.getenv("ADK_DEFAULT_MODEL", DEFAULT_MODEL))


def get_thinking_model() -> str:
    """
    获取思考 agent 模型配置。
    注意：此模型必须支持内置思考功能（如 Gemini 2.5+）。

    Returns:
        模型名称字符串
    """
    # 思考模型默认使用 GLM-4，如果需要 thinking 功能则需要 Gemini 2.5+
    default_thinking = os.getenv("ADK_DEFAULT_MODEL", "gemini-2.5-flash")
    return os.getenv("ADK_THINKING_MODEL", default_thinking)


# 导出所有配置函数
__all__ = [
    "get_default_model",
    "get_coordinator_model",
    "get_executor_model",
    "get_react_model",
    "get_thinking_model",
    "DEFAULT_MODEL",
    "ModelConfig",
]