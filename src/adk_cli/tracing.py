"""
OpenTelemetry Tracing 配置示例

ADK 内置 OpenTelemetry 支持
===========================

ADK 自带完整的 OpenTelemetry (OTel) 集成，支持：
- **Traces**: 追踪 agent 执行、工具调用、LLM 请求
- **Metrics**: Token 使用量、延迟等指标
- **Logs**: 结构化日志

自动追踪的操作：
----------------
1. `invoke_agent` - Agent 调用
2. `execute_tool` - 工具执行
3. `generate_content` - LLM 推理调用

ADK Trace 属性（Semantic Conventions）：
---------------------------------------
- `gen_ai.operation_name`: 操作类型
- `gen_ai.agent.name`: Agent 名称
- `gen_ai.agent.description`: Agent 描述
- `gen_ai.conversation_id`: 会话 ID
- `gen_ai.tool.name`: 工具名称
- `gen_ai.usage.input_tokens`: 输入 token 数
- `gen_ai.usage.output_tokens`: 输出 token 数

启用方式：
----------
方式 1: 环境变量（推荐）
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
    # 或分别配置：
    export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4318/v1/traces
    export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:4318/v1/metrics
    export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://localhost:4318/v1/logs

方式 2: 代码中调用 maybe_set_otel_providers()

方式 3: 使用 GCP exporters (Cloud Trace, Cloud Monitoring, Cloud Logging)

内容捕获控制：
-------------
export ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=true  # 默认 true
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true  # 捕获 prompt/response
"""

import os
from typing import Optional

from google.adk.telemetry.setup import maybe_set_otel_providers, OTelHooks
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter


def setup_tracing(
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
    service_name: str = "adk-cli-demo",
) -> None:
    """配置 OpenTelemetry tracing。

    配置方式说明：
    --------------
    1. **OTLP Exporter**:
       - 发送到 OTLP 兼容的后端（Jaeger, Prometheus, 等）
       - 需要设置 endpoint URL

    2. **Console Exporter**:
       - 打印 spans 到控制台
       - 用于开发和调试

    3. **环境变量**:
       - OTEL_EXPORTER_OTLP_ENDPOINT: 通用端点
       - OTEL_SERVICE_NAME: 服务名称

    Args:
        otlp_endpoint: OTLP collector 端点 URL
        enable_console_export: 是否输出到控制台
        service_name: 服务名称（用于 resource）
    """
    # 设置服务名称
    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)

    # 构建 processors/readers 列表
    span_processors: list[SpanProcessor] = []
    metric_readers: list[MetricReader] = []

    # 添加 OTLP exporter
    if otlp_endpoint:
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otlp_endpoint
        # ADK 会自动检测并配置

    # 添加 Console exporter（调试用）
    if enable_console_export:
        span_processors.append(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    # 创建 hooks 并初始化 providers
    hooks = OTelHooks(
        span_processors=span_processors,
        metric_readers=metric_readers,
    )

    maybe_set_otel_providers([hooks])

    print(f"[OTel] Tracing initialized: service={service_name}")
    if otlp_endpoint:
        print(f"[OTel] OTLP endpoint: {otlp_endpoint}")
    if enable_console_export:
        print("[OTel] Console export enabled")


def setup_gcp_tracing(
    project_id: Optional[str] = None,
    enable_tracing: bool = True,
    enable_metrics: bool = False,
    enable_logging: bool = False,
) -> None:
    """配置 Google Cloud Tracing。

    使用 Google Cloud 服务：
    -----------------------
    - Cloud Trace: 分布式追踪
    - Cloud Monitoring: 指标监控
    - Cloud Logging: 结构化日志

    前置条件：
    ----------
    1. gcloud auth login
    2. 启用 Cloud Trace API
    3. 安装: pip install opentelemetry-exporter-gcp-trace

    Args:
        project_id: GCP 项目 ID
        enable_tracing: 启用 Cloud Trace
        enable_metrics: 启用 Cloud Monitoring
        enable_logging: 启用 Cloud Logging
    """
    try:
        from google.adk.telemetry.google_cloud import get_gcp_exporters, get_gcp_resource

        exporters = get_gcp_exporters(
            enable_cloud_tracing=enable_tracing,
            enable_cloud_metrics=enable_metrics,
            enable_cloud_logging=enable_logging,
        )

        resource = get_gcp_resource(project_id)

        maybe_set_otel_providers([exporters], resource)

        print(f"[OTel] GCP Tracing initialized: project={project_id}")
    except ImportError as e:
        print(f"[OTel] GCP exporters not available: {e}")
        print("[OTel] Install with: pip install opentelemetry-exporter-gcp-trace")


# ============================================================================
# Trace 数据解读指南
# ============================================================================
#
# 一个典型的 ADK trace 结构：
#
# Span: invoke_agent (root_agent)
#   ├── 属性:
#   │   ├── gen_ai.operation_name = "invoke_agent"
#   │   ├── gen_ai.agent.name = "adk_assistant"
#   │   └── gen_ai.conversation_id = "session_xxx"
#   │
#   ├── Span: generate_content (LLM 调用)
#   │   ├── 属性:
#   │   │   ├── gen_ai.operation.name = "generate_content"
#   │   │   ├── gen_ai.request.model = "gemini-2.0-flash"
#   │   │   ├── gen_ai.usage.input_tokens = 150
#   │   │   └── gen_ai.usage.output_tokens = 80
#   │   │
#   │   └── Event: gen_ai.choice (响应内容)
#   │
#   └── Span: execute_tool (工具调用)
#       ├── 属性:
#       │   ├── gen_ai.operation.name = "execute_tool"
#       │   ├── gen_ai.tool.name = "get_current_time"
#       │   ├── gen_ai.tool.type = "FunctionTool"
#       │   └── gcp.vertex.agent.tool_response = "2026-04-04..."
#       │
#       └── Event: gen_ai.tool.call
#
# ============================================================================
# 后端集成选项
# ============================================================================
#
# 1. **Jaeger** (本地开发推荐)
#    docker run -d --name jaeger \
#      -p 16686:16686 -p 4318:4318 \
#      jaegertracing/all-in-one:latest
#    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
#
# 2. **Google Cloud Trace** (GCP 部署推荐)
#    setup_gcp_tracing(project_id="your-project")
#
# 3. **其他 OTLP 兼容后端**
#    - Prometheus + Tempo
#    - Datadog
#    - New Relic
#    - Honeycomb
# ============================================================================