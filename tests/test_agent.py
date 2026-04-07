"""Tests for ADK CLI Demo."""

import pytest
from google.adk import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from adk_cli.agent import root_agent, time_calc_agent, memory_agent, task_agent
from adk_cli.tools import (
    get_current_time,
    calculate,
    generate_random_number,
    remember_fact,
    add_task,
    list_tasks,
)


class TestTools:
    """Test custom tools."""

    def test_get_current_time(self):
        """Test time tool returns formatted string."""
        result = get_current_time()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_current_time_custom_format(self):
        """Test time tool with custom format."""
        result = get_current_time(format="%Y-%m-%d")
        assert "-" in result

    def test_calculate_valid(self):
        """Test calculator with valid expression."""
        result = calculate("2 + 3")
        assert "5" in result

    def test_calculate_complex(self):
        """Test calculator with complex expression."""
        result = calculate("(10 + 5) * 2")
        assert "30" in result

    def test_calculate_invalid(self):
        """Test calculator with invalid characters."""
        result = calculate("print('hello')")
        assert "Error" in result

    def test_generate_random_number(self):
        """Test random number generation."""
        result = generate_random_number(1, 10)
        assert 1 <= result <= 10

    def test_generate_random_number_range(self):
        """Test random number in different range."""
        result = generate_random_number(50, 100)
        assert 50 <= result <= 100


class TestAgentStructure:
    """Test agent architecture."""

    def test_root_agent_exists(self):
        """Test root agent is properly configured."""
        assert root_agent is not None
        assert root_agent.name == "adk_assistant"

    def test_sub_agents_exist(self):
        """Test sub-agents are configured."""
        assert len(root_agent.sub_agents) == 4

        sub_agent_names = [a.name for a in root_agent.sub_agents]
        assert "time_calc_agent" in sub_agent_names
        assert "memory_agent" in sub_agent_names
        assert "task_agent" in sub_agent_names
        assert "analysis_agent" in sub_agent_names

    def test_agent_tools(self):
        """Test agents have tools configured."""
        assert len(root_agent.tools) > 0
        assert len(time_calc_agent.tools) == 3
        assert len(memory_agent.tools) == 4
        assert len(task_agent.tools) == 3

    def test_agent_model(self):
        """Test agent model configuration."""
        assert time_calc_agent.model == "gemini-2.0-flash"


class TestStateManagement:
    """Test state management capabilities."""

    @pytest.fixture
    def mock_tool_context(self):
        """Create a mock tool context."""
        class MockState:
            def __init__(self):
                self._data = {}

            def get(self, key, default=None):
                return self._data.get(key, default)

            def __getitem__(self, key):
                return self._data[key]

            def __setitem__(self, key, value):
                self._data[key] = value

            def __contains__(self, key):
                return key in self._data

        class MockToolContext:
            def __init__(self):
                self.state = MockState()

        return MockToolContext()

    def test_remember_fact(self, mock_tool_context):
        """Test fact storage."""
        result = remember_fact("test fact", mock_tool_context)
        assert "test fact" in result
        assert "remembered_facts" in mock_tool_context.state

    def test_add_task(self, mock_tool_context):
        """Test task addition."""
        result = add_task("Test task", "high", mock_tool_context)
        assert "Test task" in result
        assert "tasks" in mock_tool_context.state

    def test_list_tasks_empty(self, mock_tool_context):
        """Test listing empty tasks."""
        result = list_tasks(mock_tool_context)
        assert "No tasks" in result


@pytest.mark.asyncio
class TestRunner:
    """Test agent runner functionality."""

    @pytest.fixture
    def runner(self):
        """Create a test runner."""
        return Runner(
            app_name="test_app",
            agent=root_agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
        )

    async def test_runner_creation(self, runner):
        """Test runner is created successfully."""
        assert runner is not None
        assert runner.app_name == "test_app"
        assert runner.agent is not None

    async def test_session_creation(self, runner):
        """Test session can be created."""
        session = await runner.session_service.create_session(
            app_name="test_app",
            user_id="test_user",
        )
        assert session is not None
        assert session.user_id == "test_user"