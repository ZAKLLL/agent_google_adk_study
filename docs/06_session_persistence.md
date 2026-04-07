# Session 持久化

## 概述

ADK 内置 Session 持久化支持，无需手动实现。

## Session Service 类型

### 1. InMemorySessionService

```python
from google.adk.sessions import InMemorySessionService

# 内存模式（默认）
session_service = InMemorySessionService()

# 特点：
# - 会话数据保存在内存中
# - 进程重启后丢失
# - 适合测试和开发
```

### 2. SqliteSessionService（推荐）

```python
from google.adk.sessions import SqliteSessionService

# SQLite 持久化
session_service = SqliteSessionService("sessions.db")

# 特点：
# - 自动创建数据库文件
# - 支持会话恢复
# - 零配置，单文件存储
# - 适合单机生产环境
```

### 3. DatabaseSessionService

```python
from google.adk.sessions import DatabaseSessionService

# SQLAlchemy 支持
session_service = DatabaseSessionService(
    "postgresql://user:pass@localhost/db"
)

# 特点：
# - 支持 PostgreSQL, MySQL, SQLite 等
# - 适合分布式生产环境
```

---

## 使用方式

### 创建 Runner

```python
from google.adk import Runner
from google.adk.sessions import SqliteSessionService

runner = Runner(
    app_name="my_app",
    agent=agent,
    session_service=SqliteSessionService("sessions.db"),
)
```

### 创建会话

```python
# 创建新会话
session = await runner.session_service.create_session(
    app_name="my_app",
    user_id="user123",
)

print(f"Session ID: {session.id}")  # 自动生成的 UUID
```

### 恢复会话

```python
# 获取已有会话
session = await runner.session_service.get_session(
    app_name="my_app",
    user_id="user123",
    session_id="previous_session_id",
)

if session:
    print(f"Resumed session with {len(session.events)} events")
else:
    print("Session not found")
```

### 列出会话

```python
response = await runner.session_service.list_sessions(
    app_name="my_app",
    user_id="user123",
)

for session in response.sessions:
    print(f"Session: {session.id}")
    print(f"Events: {len(session.events)}")
    print(f"Last update: {session.last_update_time}")
```

---

## 数据结构

### Session 对象

```python
class Session:
    id: str                    # 会话 ID
    app_name: str              # 应用名称
    user_id: str               # 用户 ID
    state: dict                # 会话状态
    events: list[Event]        # 事件历史
    last_update_time: float    # 最后更新时间
```

### State 前缀

```python
# 会话级状态
session.state["tasks"] = ["task1", "task2"]

# 用户级状态（跨会话）
session.state["user:preferences"] = {"lang": "zh"}

# 应用级状态（跨用户）
session.state["app:config"] = {"version": "1.0"}

# 临时状态（不持久化）
session.state["temp:cache"] = {"data": "..."}
```

---

## 持久化内容

Session 持久化包括：

```
sessions.db
├── sessions 表
│   ├── id
│   ├── app_name
│   ├── user_id
│   ├── state (JSON)
│   └── last_update_time
│
├── events 表
│   ├── id
│   ├── session_id
│   ├── timestamp
│   ├── author
│   ├── content (JSON)
│   └── actions (JSON)
│
└── states 表
    ├── app_states
    ├── user_states
    └── session_states
```

---

## 实战示例

### CLI Resume 功能

```python
# 开始新会话
$ adk-cli chat
Session ID: abc123

# 用户退出
> exit
Session saved: abc123
Resume: adk-cli resume abc123

# 恢复会话
$ adk-cli resume abc123
✓ Resumed session: abc123
> What did we discuss last time?
```

### 实现代码

```python
# cli.py

async def run_interactive_session(runner, user_id, session_id, resume):
    session_service = runner.session_service

    if resume:
        # 尝试恢复已有会话
        session = await session_service.get_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        if session:
            print(f"✓ Resumed session: {session_id}")
        else:
            print(f"Session not found: {session_id}")
            return
    else:
        # 创建新会话
        session = await session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
        )
        print(f"✓ New session: {session.id}")

    # 交互循环
    while True:
        user_input = input("> ")

        if user_input == "exit":
            print(f"Session saved: {session.id}")
            print(f"Resume: adk-cli resume {session.id}")
            break

        # 运行 Agent
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_input)],
            ),
        ):
            # 处理事件
            ...
```

---

## 最佳实践

### 1. 会话 ID 管理

```python
# ✅ 使用有意义的会话 ID
session_id = f"support_ticket_{ticket_id}"

# ✅ 或让 ADK 自动生成
session = await session_service.create_session(...)

# ❌ 不要使用硬编码 ID
session_id = "my_session"  # 可能冲突
```

### 2. 定期清理

```python
import asyncio
from datetime import datetime, timedelta

async def cleanup_old_sessions(session_service, days=30):
    """清理旧会话"""
    cutoff = datetime.now() - timedelta(days=days)

    # 获取所有会话
    response = await session_service.list_sessions(...)

    for session in response.sessions:
        last_update = datetime.fromtimestamp(session.last_update_time)
        if last_update < cutoff:
            await session_service.delete_session(
                app_name=session.app_name,
                user_id=session.user_id,
                session_id=session.id,
            )
```

### 3. 数据目录管理

```python
from pathlib import Path

# 使用标准数据目录
DATA_DIR = Path.home() / ".my_app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

session_service = SqliteSessionService(DATA_DIR / "sessions.db")
```

---

**Next**: [OpenTelemetry Tracing](07_tracing.md)