# OpenTelemetry Tracing

## 概述

ADK 内置 OpenTelemetry 支持，无需手动集成。

## 启用 Tracing

### CLI 启用

```bash
# 启用 tracing（输出到控制台）
adk-cli --trace chat

# 发送到 OTLP Collector
adk-cli --trace --otlp-endpoint http://localhost:4318 chat
```

### 代码启用

```python
from google.adk.telemetry import setup_tracing

# 启用 tracing
setup_tracing(
    otlp_endpoint="http://localhost:4318",  # OTLP Collector 地址
    service_name="my-adk-app",              # 服务名称
)
```

---

## 本地 Jaeger 集成

### 启动 Jaeger

```bash
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

# 访问 UI: http://localhost:16686
# OTLP 端点: http://localhost:4318
```

### 运行 ADK

```bash
adk-cli --trace --otlp-endpoint http://localhost:4318 chat
```

---

## Trace 数据结构

```
Span: invoke_agent (adk_assistant)
  ├── gen_ai.agent.name = "adk_assistant"
  ├── gen_ai.conversation_id = "session_xxx"
  │
  ├── Span: call_llm
  │   ├── gen_ai.request.model = "gemini-2.0-flash"
  │   ├── gen_ai.usage.input_tokens = 150
  │   │
  │   ├── Span: execute_tool (get_current_time)
  │   │   └── gen_ai.tool.name = "get_current_time"
  │   │
  │   └── Span: execute_tool (calculate)
  │       └── gen_ai.tool.name = "calculate"
  │
  └── gen_ai.usage.output_tokens = 200
```

---

## Semantic Conventions

ADK 遵循 OpenTelemetry Semantic Conventions：

```python
# 源码: adk-python/src/google/adk/telemetry/_experimental_semconv.py

# Agent 属性
gen_ai.agent.name           # Agent 名称
gen_ai.conversation_id      # 会话 ID

# Model 属性
gen_ai.request.model        # 模型名称
gen_ai.usage.input_tokens   # 输入 token 数
gen_ai.usage.output_tokens  # 输出 token 数

# Tool 属性
gen_ai.tool.name            # 工具名称
gen_ai.tool.call.id         # 函数调用 ID
```

---

## 自定义 Span

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def my_custom_operation():
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("custom.key", "value")
        span.add_event("processing_started")

        # 执行操作
        result = await do_something()

        span.set_attribute("custom.result", result)
        return result
```

---

## Trace 分析

### 在 Jaeger 中查看

1. 打开 http://localhost:16686
2. 选择 Service: `my-adk-app`
3. 查找 Trace
4. 分析延迟和调用链

### 关键指标

- **LLM 调用延迟**: `call_llm` span 持续时间
- **工具执行时间**: `execute_tool` span 持续时间
- **Token 消耗**: `gen_ai.usage.*` 属性
- **错误追踪**: span 状态和错误事件

---

## 最佳实践

### 1. 生产环境采样

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# 采样 10% 的 trace
provider = TracerProvider(sampler=TraceIdRatioBased(0.1))
```

### 2. 添加业务属性

```python
from google.adk.plugins import BasePlugin

class TracingPlugin(BasePlugin):
    async def before_agent_callback(self, *, callback_context, **kwargs):
        from opentelemetry import trace
        span = trace.get_current_span()
        span.set_attribute("user.id", callback_context.user_id)
        span.set_attribute("session.id", callback_context.session_id)
```

### 3. 错误追踪

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

async def risky_operation():
    with tracer.start_as_current_span("risky") as span:
        try:
            result = await do_something()
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

---

## 与其他系统集成

### Prometheus

```python
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider

prometheus_reader = PrometheusMetricReader()
meter_provider = MeterProvider(metric_readers=[prometheus_reader])
```

### Google Cloud Trace

```python
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

exporter = CloudTraceSpanExporter()
# 自动发送到 Google Cloud Trace
```

---

**Next**: [ReAct 模式](08_react_mode.md)