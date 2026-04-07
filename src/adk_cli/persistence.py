"""
Session 持久化服务模块

ADK Session 持久化方案
======================

ADK 内置两种持久化方案：

1. **SqliteSessionService** (推荐)
   - 使用 SQLite 数据库
   - 零配置，单文件存储
   - 支持会话恢复、状态持久化、事件历史

2. **DatabaseSessionService**
   - 使用 SQLAlchemy
   - 支持 PostgreSQL, MySQL, SQLite 等
   - 适合生产环境

数据存储结构：
--------------
- app_states: 应用级状态
- user_states: 用户级状态
- sessions: 会话元数据
- events: 事件历史

使用方式：
----------
```python
from google.adk.sessions.sqlite_session_service import SqliteSessionService

# 创建持久化服务
session_service = SqliteSessionService("sessions.db")

# 创建 Runner
runner = Runner(
    app_name="my_app",
    agent=agent,
    session_service=session_service,  # 使用持久化
)

# 恢复会话
session = await session_service.get_session(
    app_name="my_app",
    user_id="user1",
    session_id="previous_session_id",
)
```
"""

import os
from pathlib import Path
from typing import Optional

from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.adk.sessions.base_session_service import BaseSessionService

# 默认数据目录
DEFAULT_DATA_DIR = Path.home() / ".adk_cli" / "data"


def get_persistent_session_service(
    db_path: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> SqliteSessionService:
    """获取持久化的 Session 服务。

    使用 SQLite 存储会话数据：
    - 会话状态
    - 事件历史
    - 用户/应用级状态

    数据文件位置：
    - 默认: ~/.adk_cli/data/sessions.db
    - 可自定义路径

    Args:
        db_path: 数据库文件路径（完整路径）
        data_dir: 数据目录（使用默认文件名）

    Returns:
        SqliteSessionService 实例
    """
    if db_path:
        # 使用指定的数据库路径
        db_file = db_path
    else:
        # 使用默认数据目录
        data_path = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        data_path.mkdir(parents=True, exist_ok=True)
        db_file = str(data_path / "sessions.db")

    return SqliteSessionService(db_file)


def get_data_dir() -> Path:
    """获取数据目录路径。"""
    return DEFAULT_DATA_DIR


def ensure_data_dir() -> Path:
    """确保数据目录存在并返回路径。"""
    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DATA_DIR