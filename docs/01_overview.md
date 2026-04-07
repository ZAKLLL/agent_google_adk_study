# 框架概览

## 什么是 ADK？

ADK (Agent Development Kit) 是 Google 开发的 Agent 开发框架，提供：

- **Agent 抽象**: 统一的 Agent 定义接口
- **工具系统**: 灵活的工具定义与执行
- **会话管理**: 完整的 Session 生命周期管理
- **多 Agent 协作**: 原生的 Agent 间通信与协作
- **可观测性**: 内置 OpenTelemetry 支持

## 核心组件

```Markdown
┌─────────────────────────────────────────────────────────────┐
│                        Runner                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Agent Tree                        │    │
│  │  ┌─────────────┐                                    │    │
│  │  │ root_agent  │──────┬──────┬──────┬──────        │    │
│  │  │ (coordinator)│      │      │      │             │    │
│  │  └─────────────┘      │      │      │             │    │
│  │                       ↓      ↓      ↓              │    │
│  │              ┌────────┴────────┴────────┐          │    │
│  │              │  sub_agents (executors)  │          │    │
│  │              │  - time_agent            │          │    │
│  │              │  - calc_agent            │          │    │
│  │              │  - memory_agent          │          │    │
│  │              └──────────────────────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │SessionService│  │ArtifactService│  │MemoryService │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## 关键导入

```python
from google.adk import Runner
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.tools import FunctionTool
from google.adk.sessions import InMemorySessionService, SqliteSessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types
```

## 最小示例

```python
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 1. 定义 Agent
agent = LlmAgent(
    name="simple_agent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
)

# 2. 创建 Runner
runner = Runner(
    app_name="my_app",
    agent=agent,
    session_service=InMemorySessionService(),
)

# 3. 运行
async def main():
    session = await runner.session_service.create_session(
        app_name="my_app", user_id="user1"
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text="Hello!")],
    )

    async for event in runner.run_async(
        user_id="user1",
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)
```

## 设计哲学

ADK 的设计理念：

1. **声明式配置**: Agent 通过配置定义，而非代码逻辑
2. **事件驱动**: 所有交互通过 Event 流传递
3. **状态隔离**: Session/State/Artifact 分层管理
4. **框架即用**: 内置大量常用功能，减少自定义代码

***

## 与其他框架对比

| 特性       | ADK             | LangChain | AutoGen |
| -------- | --------------- | --------- | ------- |
| Agent 定义 | 声明式             | 链式        | 类继承     |
| 多 Agent  | 原生支持            | 需编排       | 核心特性    |
| 工具系统     | FunctionTool    | Tool 抽象   | 函数装饰器   |
| 状态管理     | Session Service | Memory    | 无内置     |
| Tracing  | 内置 OTel         | 需集成       | 无内置     |

***

**Next**: [Agent 类型与架构](02_agent_types.md)
