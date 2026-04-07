# ADK 高级特性

本文档记录 ADK 的高级特性，适合在掌握基础后深入学习。

---

## 1. Memory Service（长期记忆）

### 概述

Memory Service 提供跨会话的长期记忆能力，区别于 Session State 的会话级存储。

### 核心接口

```python
# 源码: adk-python/src/google/adk/memory/base_memory_service.py

class BaseMemoryService(ABC):
    async def add_session_to_memory(self, session: Session) -> None:
        """将整个会话添加到记忆"""

    async def add_events_to_memory(
        self, *, app_name, user_id, events, session_id=None
    ) -> None:
        """添加特定事件到记忆"""

    async def search_memory(
        self, *, app_name, user_id, query
    ) -> SearchMemoryResponse:
        """搜索记忆"""
```

### 实现类型

| 实现 | 说明 | 适用场景 |
|------|------|----------|
| `InMemoryMemoryService` | 内存存储 | 测试 |
| `VertexAiRagMemoryService` | Vertex AI RAG | 生产环境 |
| `VertexAiMemoryBankService` | Vertex AI Memory Bank | 企业级 |

### 使用示例

```python
from google.adk.memory import VertexAiRagMemoryService

memory_service = VertexAiRagMemoryService(
    rag_corpus="projects/.../locations/.../ragCorpora/..."
)

runner = Runner(
    agent=agent,
    memory_service=memory_service,
)

# 会话结束后，将内容添加到长期记忆
await memory_service.add_session_to_memory(session)

# 在新会话中搜索历史记忆
results = await memory_service.search_memory(
    app_name="my_app",
    user_id="user123",
    query="What did the user prefer?",
)
```

---

## 2. Artifact Service（文件管理）

### 概述

Artifact Service 用于管理二进制文件（图片、文档、音频等），支持版本控制。

### 核心接口

```python
# 源码: adk-python/src/google/adk/artifacts/base_artifact_service.py

class BaseArtifactService(ABC):
    async def save_artifact(
        self, *, app_name, user_id, filename, artifact, session_id=None
    ) -> int:
        """保存文件，返回版本号"""

    async def load_artifact(
        self, *, app_name, user_id, filename, session_id=None, version=None
    ) -> Optional[types.Part]:
        """加载文件"""

    async def list_artifact_keys(...) -> list[str]:
        """列出所有文件名"""

    async def list_versions(...) -> list[int]:
        """列出所有版本"""
```

### 作用域

| 参数 | 作用域 |
|------|--------|
| `session_id=None` | 用户级（跨会话） |
| `session_id="xxx"` | 会话级（特定会话） |

### 实现类型

| 实现 | 说明 |
|------|------|
| `InMemoryArtifactService` | 内存存储 |
| `GcsArtifactService` | Google Cloud Storage |
| `FileArtifactService` | 本地文件系统 |

### 在 Tool 中使用

```python
from google.genai import types

async def save_document(content: str, tool_context: ToolContext) -> str:
    """保存文档到 Artifact"""
    artifact = types.Part(
        inline_data=types.Blob(
            data=content.encode(),
            mime_type="text/plain",
        )
    )

    version = await tool_context.save_artifact(
        filename="document.txt",
        artifact=artifact,
    )
    return f"Saved as version {version}"

async def load_document(tool_context: ToolContext) -> str:
    """从 Artifact 加载文档"""
    artifact = await tool_context.load_artifact("document.txt")
    return artifact.inline_data.data.decode()
```

---

## 3. A2A Protocol（Agent 间通信）

### 概述

A2A (Agent-to-Agent) 是一种标准化的 Agent 间通信协议，支持跨平台 Agent 协作。

### RemoteA2aAgent

```python
# 源码: adk-python/src/google/adk/agents/remote_a2a_agent.py

from google.adk.agents import RemoteA2aAgent

# 连接远程 Agent
remote_agent = RemoteA2aAgent(
    name="remote_assistant",
    agent_card="https://other-agent.example.com/.well-known/agent.json",
    # 或本地文件
    # agent_card="/path/to/agent_card.json",
)

# 像本地 Agent 一样使用
runner = Runner(
    agent=remote_agent,
    ...
)
```

### Agent Card

Agent Card 描述了远程 Agent 的能力：

```json
{
  "name": "Weather Agent",
  "description": "Provides weather information",
  "url": "https://weather-agent.example.com/rpc",
  "capabilities": {
    "streaming": true,
    "tools": ["get_weather", "get_forecast"]
  }
}
```

---

## 4. MCP Toolset（Model Context Protocol）

### 概述

MCP 是 Anthropic 推出的工具协议标准，ADK 支持直接集成 MCP 服务器。

### 使用方式

```python
# 源码: adk-python/src/google/adk/tools/mcp_tool/mcp_toolset.py

from google.adk.tools import McpToolset
from mcp import StdioServerParameters

# 连接 MCP 服务器
mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command='npx',
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"],
    ),
    tool_filter=['read_file', 'list_directory'],  # 可选：过滤工具
)

# 在 Agent 中使用
agent = LlmAgent(
    tools=[mcp_toolset],
)

# 清理连接
await mcp_toolset.close()
```

### 支持的连接方式

| 方式 | 说明 |
|------|------|
| `StdioServerParameters` | 通过 stdio 启动 MCP 服务器 |
| `SseConnectionParams` | 通过 SSE 连接远程 MCP 服务器 |
| `StreamableHTTPConnectionParams` | 通过 HTTP 连接 |

---

## 5. Long Running Tool（长时间运行工具）

### 概述

对于耗时操作（如数据处理、文件生成），使用 `LongRunningFunctionTool` 避免 Agent 超时。

### 使用方式

```python
from google.adk.tools import LongRunningFunctionTool

async def process_large_file(file_id: str, tool_context: ToolContext) -> str:
    """处理大文件（可能需要几分钟）"""
    # 返回中间状态
    # Agent 会继续其他任务，等待最终结果

    result = await long_running_process(file_id)
    return result

# 使用 LongRunningFunctionTool 包装
tool = LongRunningFunctionTool(process_large_file)
```

### 自动注入提示

```
NOTE: This is a long-running operation. Do not call this tool
again if it has already returned some intermediate or pending status.
```

---

## 6. Streaming Mode（流式输出）

### 模式类型

```python
# 源码: adk-python/src/google/adk/agents/run_config.py

from google.adk.agents.run_config import RunConfig, StreamingMode

# SSE 流式（适合 Web UI）
run_config = RunConfig(
    streaming_mode=StreamingMode.SSE,
)

# 双向流式（Live API）
run_config = RunConfig(
    streaming_mode=StreamingMode.BIDI,
)
```

### SSE 流式处理

```python
config = RunConfig(streaming_mode=StreamingMode.SSE)

async for event in runner.run_async(..., run_config=config):
    if event.partial:
        # 部分响应（打字机效果）
        if event.content and event.content.parts:
            text = ''.join(p.text or '' for p in event.content.parts)
            print(text, end='', flush=True)
    else:
        # 完整响应
        ...
```

---

## 7. Code Execution（代码执行）

### 概述

ADK 支持让 Agent 执行代码，用于计算、数据分析等场景。

### 使用方式

```python
from google.adk.code_executors import CodeExecutionUtils

# Agent 生成的代码会自动执行
# 支持输入/输出文件
```

---

## 8. Evaluation（Agent 评估）

### 概述

ADK 提供完整的 Agent 评估框架，支持多维度质量评估。

### 核心组件

```python
# 源码: adk-python/src/google/adk/evaluation/

# 评估指标
- FinalResponseMatchEvaluator  # 最终响应匹配
- ToolUseQualityEvaluator      # 工具使用质量
- TrajectoryQualityEvaluator   # 轨迹质量
- SafetyEvaluator              # 安全性评估
- HallucinationsEvaluator      # 幻觉检测

# 用户模拟器
- UserSimulator                # 模拟用户行为
- LLMBackedUserSimulator       # LLM 驱动的用户模拟
```

### 使用示例

```python
from google.adk.evaluation import AgentEvaluator

evaluator = AgentEvaluator(
    agent=my_agent,
    eval_set=eval_set,
)

results = await evaluator.evaluate()

for result in results:
    print(f"Metric: {result.metric_name}, Score: {result.score}")
```

---

## 9. Live API（实时交互）

### 概述

支持实时语音、视频交互，适合对话式 Agent。

### 使用方式

```python
# 使用 run_live() 而非 run_async()
async for event in runner.run_live(
    user_id=user_id,
    session_id=session_id,
):
    # 处理实时事件
    ...
```

### RunConfig 高级选项

```python
run_config = RunConfig(
    speech_config=types.SpeechConfig(...),
    response_modalities=["AUDIO"],
    enable_affective_dialog=True,  # 情感对话
    proactivity=types.ProactivityConfig(...),  # 主动响应
)
```

---

## 10. Context Window Compression（上下文压缩）

### 概述

自动压缩长对话历史，避免超出 token 限制。

### 使用方式

```python
from google.genai import types

run_config = RunConfig(
    context_window_compression=types.ContextWindowCompressionConfig(
        # 压缩配置
    ),
)
```

---

## 高级特性学习优先级

```
┌─────────────────────────────────────────────────────────────────────┐
│                    高级特性学习优先级建议                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ★★★ 必须掌握                                                        │
│  ├── Memory Service      - 长期记忆，生产必备                        │
│  ├── Artifact Service    - 文件管理，常用功能                        │
│  └── Streaming Mode      - 用户体验，Web 必备                        │
│                                                                      │
│  ★★☆ 重要掌握                                                        │
│  ├── A2A Protocol        - 多 Agent 协作                            │
│  ├── MCP Toolset         - 工具扩展                                  │
│  └── Evaluation          - 质量保障                                  │
│                                                                      │
│  ★☆☆ 进阶掌握                                                        │
│  ├── Long Running Tool   - 特定场景                                  │
│  ├── Code Execution      - 数据分析场景                              │
│  ├── Live API            - 实时交互场景                              │
│  └── Context Compression - 长对话场景                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

**Back to**: [目录](README.md)