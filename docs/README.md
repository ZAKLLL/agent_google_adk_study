# ADK 学习笔记

> 记录 Google ADK (Agent Development Kit) 框架的核心概念与内部机制。

---

## 目录

1. [框架概览](01_overview.md)
2. [Agent 类型与架构](02_agent_types.md)
3. [协调器/执行者模式](03_coordinator_executor.md)
4. [工具系统](04_tool_system.md)
5. [回调系统](05_callback_system.md)
6. [Session 持久化](06_session_persistence.md)
7. [OpenTelemetry Tracing](07_tracing.md)
8. [ReAct 模式](08_react_mode.md)
9. [执行流程：内部循环机制](09_execution_flow.md)
10. [上下文管理策略](10_context_management.md)
11. [内置 Prompt 体系](11_builtin_prompts.md)
12. [高级特性](12_advanced_features.md) ⭐ **新增**

---

## 快速索引

| 主题 | 关键发现 |
|------|----------|
| Agent 类型 | LlmAgent, SequentialAgent, ParallelAgent, LoopAgent |
| 协调器模式 | root_agent + sub_agents + transfer_to_agent |
| 工具系统 | FunctionTool + ToolContext 状态访问 |
| 回调层级 | agent/model/tool 三层 before/after 回调 |
| 持久化 | SqliteSessionService 内置支持 |
| Tracing | OpenTelemetry 内置集成 |
| ReAct | PlanReActPlanner (显式标签) / BuiltInPlanner (Gemini 2.5+) |
| 执行流程 | **不是一问一答**，内部 while 循环直到 is_final_response() |
| 上下文管理 | 默认全传历史，ContextFilterPlugin 可截断 |
| 内置 Prompt | Identity + Transfer + ReAct 自动注入，**无本地化** |
| Memory Service | 跨会话长期记忆，支持 RAG 检索 |
| Artifact Service | 二进制文件管理，支持版本控制 |
| A2A Protocol | Agent 间标准化通信协议 |
| MCP Toolset | 集成 Model Context Protocol 工具 |

---

## 项目结构

```
src/adk_cli/
├── agent.py          # Agent 定义（协调器/执行者）
├── react_agent.py    # ReAct 模式示例
├── tools.py          # 12 个自定义工具
├── callbacks.py      # 回调系统示例
├── cli.py            # CLI 入口
├── tracing.py        # OTel 配置
├── persistence.py    # Session 持久化
└── utils.py          # 工具函数
```

---

## 学习历程

### Day 1: 基础概念

- 理解 ADK 的核心组件：Agent, Tool, Session, Runner
- 创建第一个 CLI 应用
- 实现基础的交互式聊天

### Day 2: Agent 架构

- 发现协调器/执行者模式
- 理解 transfer_to_agent 机制
- 实现多 Agent 协作

### Day 3: 工具与回调

- 定义自定义工具
- 理解 ToolContext 状态访问
- 实现回调函数

### Day 4: 持久化与追踪

- 发现 SqliteSessionService
- 实现 session resume
- 集成 OpenTelemetry

### Day 5: ReAct 模式

- 理解 PlanReActPlanner vs BuiltInPlanner
- 实现显式推理链
- 对比两种 Planner

### Day 6: 内部机制深入

- **关键发现**: ADK 内部有 while 循环，不是一问一答
- 理解上下文管理策略
- 分析内置 Prompt 体系

### Day 7: 高级特性探索

- Memory Service：跨会话长期记忆
- Artifact Service：文件版本管理
- A2A Protocol：远程 Agent 通信
- MCP Toolset：工具生态扩展
- Evaluation：质量评估体系

---

## Google ADK 深度学习路线

### 阶段一：基础掌握（1-2 周）

| 学习内容 | 资源 | 实践任务 |
|----------|------|----------|
| ADK 核心概念 | [官方文档](https://google.github.io/adk-docs/) | 阅读 Overview 和 Quickstart |
| Agent 类型 | [02_agent_types.md](02_agent_types.md) | 创建 LlmAgent、SequentialAgent |
| 工具系统 | [04_tool_system.md](04_tool_system.md) | 定义 3 个自定义工具 |
| Session 管理 | [06_session_persistence.md](06_session_persistence.md) | 实现 session resume |

**里程碑**：完成一个 CLI 聊天应用，支持持久化会话。

### 阶段二：架构深入（2-3 周）

| 学习内容 | 资源 | 实践任务 |
|----------|------|----------|
| 协调器/执行者模式 | [03_coordinator_executor.md](03_coordinator_executor.md) | 实现多 Agent 协作 |
| 回调系统 | [05_callback_system.md](05_callback_system.md) | 实现日志记录和过滤回调 |
| 执行流程 | [09_execution_flow.md](09_execution_flow.md) | 阅读 `base_llm_flow.py` 源码 |
| 上下文管理 | [10_context_management.md](10_context_management.md) | 实现 ContextFilterPlugin |

**里程碑**：实现一个多 Agent 协作系统，支持 Agent Transfer。

### 阶段三：高级特性（3-4 周）

| 学习内容 | 资源 | 实践任务 |
|----------|------|----------|
| ReAct 模式 | [08_react_mode.md](08_react_mode.md) | 对比两种 Planner 的效果 |
| 内置 Prompt | [11_builtin_prompts.md](11_builtin_prompts.md) | 自定义 Global Instruction |
| OpenTelemetry | [07_tracing.md](07_tracing.md) | 集成 Jaeger 追踪 |
| LoopAgent + Human-in-loop | [05_callback_system.md](05_callback_system.md) | 实现迭代优化流程 |

**里程碑**：实现一个 ReAct Agent，支持 Tracing 和 Human-in-loop。

### 阶段四：高级特性（4-6 周）

#### 必须掌握

| 学习内容 | 资源 | 实践任务 |
|----------|------|----------|
| Memory Service | [12_advanced_features.md](12_advanced_features.md) | 实现跨会话记忆 |
| Artifact Service | [12_advanced_features.md](12_advanced_features.md) | 实现文件上传/下载 |
| Streaming Mode | [12_advanced_features.md](12_advanced_features.md) | 实现流式输出 UI |

#### 重要掌握

| 学习内容 | 资源 | 实践任务 |
|----------|------|----------|
| A2A Protocol | [12_advanced_features.md](12_advanced_features.md) | 连接远程 Agent |
| MCP Toolset | [12_advanced_features.md](12_advanced_features.md) | 集成 MCP 工具 |
| Evaluation | [12_advanced_features.md](12_advanced_features.md) | 编写评估用例 |

#### 进阶掌握

| 学习内容 | 资源 | 实践任务 |
|----------|------|----------|
| Long Running Tool | [12_advanced_features.md](12_advanced_features.md) | 实现异步任务 |
| Code Execution | [12_advanced_features.md](12_advanced_features.md) | 实现代码沙箱 |
| Live API | [12_advanced_features.md](12_advanced_features.md) | 实现实时对话 |

**里程碑**：实现一个生产级 Agent 应用，支持长期记忆、流式输出、质量评估。

### 阶段六：源码研究（持续）

| 模块 | 源码路径 | 重点理解 |
|------|----------|----------|
| Agent 核心 | `adk-python/src/google/adk/agents/` | Agent 生命周期、状态管理 |
| 执行流 | `adk-python/src/google/adk/flows/llm_flows/` | 循环机制、事件处理 |
| 工具系统 | `adk-python/src/google/adk/tools/` | ToolContext、工具声明生成 |
| Session 服务 | `adk-python/src/google/adk/sessions/` | 持久化机制 |
| Planner | `adk-python/src/google/adk/planners/` | ReAct 实现 |
| Memory | `adk-python/src/google/adk/memory/` | 长期记忆实现 |
| Artifact | `adk-python/src/google/adk/artifacts/` | 文件管理实现 |
| A2A | `adk-python/src/google/adk/a2a/` | Agent 通信协议 |
| Evaluation | `adk-python/src/google/adk/evaluation/` | 评估框架 |

**实践任务**：
1. 画出 ADK 执行流程图
2. 理解 `is_final_response()` 的判断逻辑
3. 研究 function_call/response 配对机制

### 阶段七：生产实践（持续）

| 主题 | 学习内容 |
|------|----------|
| **性能优化** | Token 管理、Context 截断、缓存策略、Streaming |
| **可观测性** | Tracing 集成、指标监控、日志规范 |
| **安全性** | 工具权限控制、输入验证、输出过滤、Auth 系统 |
| **扩展性** | 自定义 SessionService、自定义 Planner、自定义 Memory |
| **质量保障** | Evaluation、User Simulation、A/B Testing |
| **高可用** | Long Running Tool、Error Handling、Retry 机制 |

### 推荐阅读顺序

```
01_overview.md           → 整体概念
02_agent_types.md        → Agent 类型
03_coordinator_executor.md → 多 Agent 架构
04_tool_system.md        → 工具定义
09_execution_flow.md     → ★ 核心理解（执行流）
10_context_management.md → 上下文策略
08_react_mode.md         → ReAct 模式
11_builtin_prompts.md    → Prompt 体系
05_callback_system.md    → 回调机制
06_session_persistence.md → 持久化
07_tracing.md            → 可观测性
12_advanced_features.md  → ★ 高级特性（生产必备）
```

### 学习资源

- **官方文档**: https://google.github.io/adk-docs/
- **源码仓库**: https://github.com/google/adk-python
- **示例仓库**: https://github.com/google/adk-samples
- **OpenTelemetry**: https://opentelemetry.io/

---

## 参考资源

- [ADK 官方文档](https://google.github.io/adk-docs/)
- [ADK Python 源码](https://github.com/google/adk-python)
- [ADK 示例仓库](https://github.com/google/adk-samples)