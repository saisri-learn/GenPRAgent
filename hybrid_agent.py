"""
Hybrid Multi-LLM Agent for GitHub PR Generation using LangChain
Model is fully configurable; complexity analysis selects model in auto mode.
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Literal
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Short aliases → full model IDs
MODEL_ALIASES = {
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-haiku": "claude-haiku-4-5-20251001",
    "claude-opus": "claude-opus-4-6",
}

# Approximate cost per token for cost tracking
COST_PER_TOKEN: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "claude-sonnet-4-6": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-haiku-4-5-20251001": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
    "claude-opus-4-6": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
}


def resolve_model(model: str) -> str:
    """Resolve a model alias to its full model ID."""
    return MODEL_ALIASES.get(model, model)


class HybridPRAgent:
    """
    Hybrid agent that can use multiple LLMs via LangChain.
    All providers share the same agent loop — only the model name differs.
    Auto mode analyzes complexity to select the optimal model.
    """

    def __init__(
        self,
        github_token: str,
        default_model: str = "gpt-4o-mini",
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize hybrid agent.

        Args:
            github_token: GitHub personal access token
            default_model: Default model to use (e.g. "gpt-4o-mini", "claude-sonnet-4-6", "auto")
            anthropic_api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
            openai_api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
        """
        self.github_token = github_token
        self.default_model = resolve_model(default_model)

        if anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        self.mcp_session: Optional[ClientSession] = None
        self.stdio_transport = None
        self.available_tools: List[Dict[str, Any]] = []

        # Cost tracking
        self.total_cost = 0.0
        self.model_usage: Dict[str, int] = {}

    async def connect_mcp(self):
        """Connect to MCP GitHub server."""
        print("🔌 Connecting to MCP GitHub server...")

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token},
        )

        self.stdio_transport = await stdio_client(server_params)
        self.mcp_session = self.stdio_transport[1]

        tools_response = await self.mcp_session.list_tools()
        self.available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools_response.tools
        ]

        tool_names = [t["name"] for t in self.available_tools]
        print(f"✅ Connected! Available tools: {', '.join(tool_names)}")

    def _as_langchain_tools(self) -> List[Dict]:
        """Convert MCP tool definitions to LangChain-compatible format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in self.available_tools
        ]

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool via MCP."""
        if not self.mcp_session:
            raise RuntimeError("MCP session not connected")
        result = await self.mcp_session.call_tool(tool_name, tool_input)
        return result.content[0].text if result.content else ""

    def _analyze_complexity(self, error_description: str) -> Literal["simple", "complex"]:
        """
        Analyze error complexity to choose appropriate model.

        Simple: single error, clear stack trace, common issue type
        Complex: multiple errors, architectural issues, security concerns
        """
        description_lower = error_description.lower()

        complex_indicators = [
            "architecture", "design", "refactor", "migrate",
            "multiple", "concurrent", "race condition", "deadlock",
            "performance", "scale", "optimize", "memory leak",
            "security", "vulnerability", "injection",
            len(error_description) > 1000,
            error_description.count("\n") > 30,
        ]

        simple_indicators = [
            "nullpointer", "undefined", "typeerror",
            "syntax error", "import error", "not found",
            "missing", "typo",
        ]

        score = 0
        for indicator in complex_indicators:
            if isinstance(indicator, bool):
                score += 1 if indicator else 0
            elif indicator in description_lower:
                score += 1

        for indicator in simple_indicators:
            if indicator in description_lower:
                score -= 1

        return "complex" if score > 1 else "simple"

    async def create_pr_from_error(
        self,
        error_description: str,
        repo: str,
        base_branch: str = "main",
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a PR using the configured model (or auto-select based on complexity).

        Args:
            error_description: Error/exception description
            repo: Repository (owner/repo)
            base_branch: Base branch
            model: Override model for this call (None = use default_model)

        Returns:
            Result dict with PR details and cost info
        """
        resolved = resolve_model(model) if model else self.default_model

        if resolved == "auto":
            complexity = self._analyze_complexity(error_description)
            resolved = "claude-sonnet-4-6" if complexity == "complex" else "gpt-4o-mini"
            print(f"🤖 Auto-detected complexity: {complexity} → {resolved}")

        print(f"\n🚀 Starting PR creation with {resolved}...")
        print(f"📝 Error: {error_description[:100]}...")

        llm = init_chat_model(resolved).bind_tools(self._as_langchain_tools())

        system_prompt = """You are a GitHub automation agent. Your task:

1. Analyze the error/exception description
2. Create a detailed draft Pull Request with:
   - Clear, concise title (under 80 characters)
   - Detailed body with:
     * Error description
     * Root cause analysis
     * Proposed solution
     * Testing recommendations
   - Mark as draft PR

Be technical, precise, and actionable."""

        user_message = f"""
Error/Exception to address:
{error_description}

Repository: {repo}
Base Branch: {base_branch}

Please create a draft PR to track and address this issue.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        pr_url = None
        max_iterations = 10

        for iteration in range(1, max_iterations + 1):
            print(f"\n🔄 Iteration {iteration} [{resolved}]...")

            response: AIMessage = await llm.ainvoke(messages)
            messages.append(response)

            # Track token usage and cost if available
            if response.usage_metadata:
                input_tokens = response.usage_metadata.get("input_tokens", 0)
                output_tokens = response.usage_metadata.get("output_tokens", 0)
                pricing = COST_PER_TOKEN.get(resolved, {})
                cost = (
                    input_tokens * pricing.get("input", 0)
                    + output_tokens * pricing.get("output", 0)
                )
                self.total_cost += cost
                self.model_usage[resolved] = self.model_usage.get(resolved, 0) + 1

            if not response.tool_calls:
                final_text = response.content if isinstance(response.content, str) else str(response.content)
                print("\n✅ Agent completed!")
                return {
                    "status": "success",
                    "message": final_text,
                    "pr_url": pr_url,
                    "model_used": resolved,
                    "iterations": iteration,
                    "total_cost": self.total_cost,
                    "cost_usd": f"${self.total_cost:.6f}",
                }

            for tool_call in response.tool_calls:
                name = tool_call["name"]
                args = tool_call["args"]
                print(f"  🔧 {name}")

                try:
                    result = await self.execute_tool(name, args)
                    print("     ✓ Success")

                    if "pull_request" in name and "html_url" in result:
                        result_data = json.loads(result)
                        pr_url = result_data.get("html_url") or result_data.get("url")

                    messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                except Exception as e:
                    print(f"     ✗ Error: {e}")
                    messages.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call["id"]))

        return {
            "status": "error",
            "message": "Max iterations reached",
            "iterations": max_iterations,
            "total_cost": self.total_cost,
        }

    async def cleanup(self):
        """Clean up MCP connection."""
        if self.stdio_transport:
            print("🔌 Disconnecting from MCP server...")
            await self.stdio_transport[0].__aexit__(None, None, None)
            print("✅ Disconnected")

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary for this session."""
        total_calls = max(sum(self.model_usage.values()), 1)
        return {
            "total_cost_usd": f"${self.total_cost:.6f}",
            "model_usage": self.model_usage,
            "average_cost_per_call": f"${self.total_cost / total_calls:.6f}",
        }


async def main():
    """Example usage"""
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("Hybrid Multi-LLM PR Agent (LangChain)")
    print("=" * 60)

    print("\nSelect model:")
    print("1. gpt-4o-mini (fast, cheap - ~$0.001/PR)")
    print("2. claude-sonnet-4-6 (best quality - ~$0.03/PR)")
    print("3. auto (analyzes complexity and selects model)")

    choice = input("\nChoice (1-3): ").strip()

    model_map = {
        "1": "gpt-4o-mini",
        "2": "claude-sonnet-4-6",
        "3": "auto",
    }

    selected_model = model_map.get(choice, "gpt-4o-mini")

    agent = HybridPRAgent(
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        default_model=selected_model,
    )

    try:
        await agent.connect_mcp()

        repo = input("\nEnter repository (owner/repo): ").strip()
        if not repo or "/" not in repo:
            print("❌ Invalid repository format")
            return

        result = await agent.create_pr_from_error(
            error_description="""
            NullPointerException in UserService.java:45

            Stack trace:
            java.lang.NullPointerException: Cannot invoke "User.getId()" because "user" is null
                at com.example.UserService.getUserById(UserService.java:45)
                at com.example.UserController.getUser(UserController.java:23)

            Issue: getUserById() returns null when user not found.
            Solution: Return Optional<User> instead of User.
            """,
            repo=repo,
        )

        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(f"Status:    {result['status']}")
        print(f"Model:     {result.get('model_used', 'N/A')}")
        print(f"Cost:      {result.get('cost_usd', 'N/A')}")
        print(f"PR URL:    {result.get('pr_url', 'N/A')}")
        print(f"Message:   {str(result['message'])[:200]}...")
        print("=" * 60)

        cost_summary = agent.get_cost_summary()
        print("\n💰 Cost Summary:")
        print(f"  Total:    {cost_summary['total_cost_usd']}")
        print(f"  Usage:    {cost_summary['model_usage']}")

    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
