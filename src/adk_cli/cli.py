"""
ADK CLI - Command-line interface for the ADK demo application.

完整功能：
- 交互式聊天 (chat)
- 单次查询 (ask)
- 会话持久化
- 恢复历史会话
- ReAct 模式
- OpenTelemetry Tracing
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from google.adk import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from .agent import root_agent
from .react_agent import react_agent, thinking_agent
from .tracing import setup_tracing
from .persistence import get_persistent_session_service

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

APP_NAME = "adk_cli_demo"


def format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def print_event(event, verbose: bool = False, show_thoughts: bool = False):
    """打印 Agent 事件。

    Args:
        event: Agent 事件
        verbose: 显示工具调用
        show_thoughts: 显示思考过程 (ReAct/thinking)
    """
    if event.partial:
        return

    author = event.author or "unknown"

    if event.content and event.content.parts:
        for part in event.content.parts:
            # 处理思考过程 (thought=True)
            if part.thought and show_thoughts:
                if part.text:
                    click.secho(f"\n  💭 [Thought]: {part.text}", fg="magenta")
                continue

            if part.text:
                if author == "user":
                    click.secho(f"\n> You: {part.text}", fg="green")
                else:
                    click.secho(f"\n{author}: {part.text}", fg="cyan")

    if verbose and event.get_function_calls():
        for fc in event.get_function_calls():
            click.secho(f"\n  [Tool Call] {fc.name}({fc.args})", fg="yellow")

    if verbose and event.get_function_responses():
        for fr in event.get_function_responses():
            response = fr.response if hasattr(fr, "response") else fr
            click.secho(f"\n  [Tool Response] {response}", fg="magenta")


async def run_interactive_session(
    runner: Runner,
    user_id: str,
    session_id: str,
    verbose: bool = False,
    resume: bool = False,
    show_thoughts: bool = False,
):
    """运行交互式会话。"""
    session_service = runner.session_service

    session = await session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )

    if session and resume:
        click.secho(f"\n✓ Resumed session: {session_id}", fg="green")
    elif session and not resume:
        session = await session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
        )
        click.secho(f"\n✓ New session: {session.id}", fg="green")
    else:
        session = await session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        click.secho(f"\n✓ New session: {session.id}", fg="green")

    click.secho("\n" + "=" * 60, fg="blue")
    click.secho("  ADK CLI - Interactive Mode", fg="blue", bold=True)
    click.secho("=" * 60, fg="blue")
    click.secho(f"  Session: {session.id}", fg="white")
    click.secho(f"  Agent: {runner.agent.name}", fg="white")
    if show_thoughts:
        click.secho("  Mode: ReAct (showing thoughts)", fg="yellow")
    click.secho("  Commands: quit, exit, clear", fg="white")
    click.secho("=" * 60 + "\n", fg="blue")

    while True:
        try:
            user_input = click.prompt(
                click.style("\nYour message", fg="green"),
                type=str,
            )

            if user_input.lower() in ["quit", "exit"]:
                click.secho(f"\nSession saved: {session.id}", fg="yellow")
                click.secho(f"Resume: adk-cli resume {session.id}", fg="yellow")
                click.secho("\nGoodbye!", fg="cyan")
                break

            if user_input.lower() == "clear":
                session = await session_service.create_session(
                    app_name=runner.app_name,
                    user_id=user_id,
                )
                click.secho(f"\nNew session: {session.id}", fg="yellow")
                continue

            if not user_input.strip():
                continue

            content = types.Content(
                role="user",
                parts=[types.Part(text=user_input)],
            )

            click.secho("\nProcessing...", fg="yellow")
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content,
            ):
                print_event(event, verbose=verbose, show_thoughts=show_thoughts)

        except KeyboardInterrupt:
            click.secho(f"\n\nSession saved: {session.id}", fg="yellow")
            click.secho("\nGoodbye!", fg="cyan")
            break
        except Exception as e:
            click.secho(f"\nError: {e}", fg="red")
            logger.error(f"Session error: {e}")


async def list_sessions(user_id: Optional[str] = None):
    """列出所有会话。"""
    session_service = get_persistent_session_service()

    response = await session_service.list_sessions(
        app_name=APP_NAME,
        user_id=user_id,
    )

    if not response.sessions:
        click.secho("\nNo sessions found.", fg="yellow")
        return

    click.secho("\n" + "=" * 70, fg="blue")
    click.secho("  Saved Sessions", fg="blue", bold=True)
    click.secho("=" * 70, fg="blue")

    for session in response.sessions:
        events_count = len(session.events) if session.events else 0
        update_time = format_timestamp(session.last_update_time)

        click.secho(f"\n  Session: {session.id}", fg="cyan")
        click.secho(f"    User: {session.user_id}", fg="white")
        click.secho(f"    Events: {events_count}", fg="white")
        click.secho(f"    Last Updated: {update_time}", fg="white")

    click.secho("\n" + "=" * 70, fg="blue")


# ============================================================================
# CLI 命令
# ============================================================================

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--trace/--no-trace", default=False, help="Enable OpenTelemetry tracing")
@click.option("--otlp-endpoint", default=None, help="OTLP collector endpoint")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, trace: bool, otlp_endpoint: Optional[str]):
    """ADK CLI Demo - Google Agent Development Kit demonstration."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if trace:
        setup_tracing(otlp_endpoint=otlp_endpoint)


@cli.command()
@click.option("--user-id", default="default_user", help="User identifier")
@click.option("--session-id", default=None, help="Session ID")
@click.option("--persist/--no-persist", default=True, help="Enable session persistence")
@click.option("--react", is_flag=True, help="Use ReAct agent (Plan-Reason-Act)")
@click.option("--thinking", is_flag=True, help="Use thinking agent (Gemini 2.5+ built-in)")
@click.pass_context
def chat(ctx: click.Context, user_id: str, session_id: Optional[str], persist: bool, react: bool, thinking: bool):
    """Start an interactive chat session.

    模式选择：
        默认         - 标准 Agent
        --react      - ReAct 模式（规划-推理-行动）
        --thinking   - 思考模式（Gemini 2.5+ 内置推理）

    示例：
        adk-cli chat                      # 标准模式
        adk-cli chat --react              # ReAct 模式
        adk-cli chat --thinking           # 思考模式
        adk-cli chat --persist            # 持久化会话
    """
    verbose = ctx.obj["verbose"]

    # 选择 Agent
    if thinking:
        agent = thinking_agent
        show_thoughts = True
        mode_name = "Thinking"
    elif react:
        agent = react_agent
        show_thoughts = True
        mode_name = "ReAct"
    else:
        agent = root_agent
        show_thoughts = False
        mode_name = "Standard"

    if persist:
        session_service = get_persistent_session_service()
    else:
        session_service = InMemorySessionService()

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
    )

    if mode_name != "Standard":
        click.secho(f"\n🧠 Mode: {mode_name}", fg="yellow")

    asyncio.run(run_interactive_session(
        runner, user_id, session_id, verbose, resume=False, show_thoughts=show_thoughts
    ))


@cli.command()
@click.argument("query")
@click.option("--user-id", default="default_user", help="User identifier")
@click.option("--session-id", default="single_query_session", help="Session ID")
@click.option("--react", is_flag=True, help="Use ReAct agent")
@click.pass_context
def ask(ctx: click.Context, query: str, user_id: str, session_id: str, react: bool):
    """Ask a single question.

    示例：
        adk-cli ask "What time is it?"
        adk-cli ask "Plan my day" --react
    """
    verbose = ctx.obj["verbose"]

    agent = react_agent if react else root_agent
    show_thoughts = react

    session_service = get_persistent_session_service()

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
    )

    async def run():
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if not session:
            session = await session_service.create_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )

        content = types.Content(role="user", parts=[types.Part(text=query)])

        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=content
        ):
            print_event(event, verbose=verbose, show_thoughts=show_thoughts)

    asyncio.run(run())


@cli.command()
@click.argument("session_id")
@click.option("--user-id", default="default_user", help="User identifier")
@click.pass_context
def resume(ctx: click.Context, session_id: str, user_id: str):
    """Resume a previous session.

    示例：
        adk-cli resume abc123
    """
    verbose = ctx.obj["verbose"]
    session_service = get_persistent_session_service()

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
    )

    asyncio.run(run_interactive_session(runner, user_id, session_id, verbose, resume=True))


@cli.command("list-sessions")
@click.option("--user-id", default=None, help="Filter by user ID")
def list_sessions_cmd(user_id: Optional[str]):
    """List all saved sessions."""
    asyncio.run(list_sessions(user_id))


@cli.command()
@click.option("--react", is_flag=True, help="Use ReAct mode")
@click.pass_context
def demo(ctx: click.Context, react: bool):
    """Run a demonstration.

    示例：
        adk-cli demo           # 标准模式
        adk-cli demo --react   # ReAct 模式
    """
    verbose = ctx.obj["verbose"]

    agent = react_agent if react else root_agent
    show_thoughts = react

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
    )

    demo_queries = [
        "Hello! What can you do?",
        "What time is it?",
        "Calculate (25 + 15) * 2",
        "Remember that I like pizza",
        "Add a task: Learn ADK ReAct mode",
        "List my tasks and recall my facts",
    ]

    click.secho("\n" + "=" * 60, fg="blue")
    click.secho(f"  ADK CLI Demo - {'ReAct' if react else 'Standard'} Mode", fg="blue", bold=True)
    click.secho("=" * 60 + "\n", fg="blue")

    async def run_demo():
        session = await runner.session_service.create_session(
            app_name=APP_NAME, user_id="demo_user"
        )

        for i, query in enumerate(demo_queries, 1):
            click.secho(f"\n[Query {i}/{len(demo_queries)}]", fg="yellow")
            click.secho(f"> {query}", fg="green")

            content = types.Content(role="user", parts=[types.Part(text=query)])

            async for event in runner.run_async(
                user_id="demo_user", session_id=session.id, new_message=content
            ):
                print_event(event, verbose=verbose, show_thoughts=show_thoughts)

            await asyncio.sleep(0.3)

        click.secho("\n" + "=" * 60, fg="blue")
        click.secho("  Demo completed!", fg="blue", bold=True)
        click.secho("=" * 60 + "\n", fg="blue")

    asyncio.run(run_demo())


@cli.command()
@click.pass_context
def info(ctx: click.Context):
    """Display architecture information."""
    click.secho("\n" + "=" * 60, fg="blue")
    click.secho("  ADK CLI - Architecture", fg="blue", bold=True)
    click.secho("=" * 60, fg="blue")

    click.secho("\n🧠 Agent Modes:", fg="cyan", bold=True)
    click.secho("  Standard    - adk-cli chat", fg="white")
    click.secho("  ReAct       - adk-cli chat --react", fg="white")
    click.secho("  Thinking    - adk-cli chat --thinking", fg="white")

    click.secho("\n🔄 ReAct Mode (Plan-Reason-Act):", fg="cyan", bold=True)
    click.secho("  /*PLANNING*/     - 制定计划", fg="white")
    click.secho("  /*REASONING*/    - 推理当前状态", fg="white")
    click.secho("  /*ACTION*/       - 执行工具", fg="white")
    click.secho("  /*FINAL_ANSWER*/ - 最终答案", fg="white")

    click.secho("\n📦 Session Persistence:", fg="cyan", bold=True)
    click.secho("  ~/.adk_cli/data/sessions.db", fg="white")
    click.secho("  adk-cli resume <session-id>", fg="white")

    click.secho("\n📊 OpenTelemetry:", fg="cyan", bold=True)
    click.secho("  adk-cli --trace chat", fg="white")

    click.secho("\n" + "=" * 60 + "\n", fg="blue")


def main():
    try:
        cli()
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


if __name__ == "__main__":
    main()