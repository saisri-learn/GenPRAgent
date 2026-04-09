"""
GitHub PR Agent using LangChain with configurable model support
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
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


def resolve_model(model: str) -> str:
    """Resolve a model alias to its full model ID."""
    return MODEL_ALIASES.get(model, model)


class GitHubPRAgent:
    """Agent that creates GitHub PRs based on error descriptions"""

    def __init__(
        self,
        github_token: str,
        model: str = "claude-sonnet-4-6",
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize the agent.

        Args:
            github_token: GitHub personal access token
            model: LangChain-compatible model name (e.g. "claude-sonnet-4-6", "gpt-4o-mini")
            anthropic_api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
            openai_api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
        """
        self.github_token = github_token
        self.model_name = resolve_model(model)

        if anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        self.llm = init_chat_model(self.model_name)
        self.mcp_session: Optional[ClientSession] = None
        self.stdio_transport = None
        self.available_tools: List[Dict[str, Any]] = []
        self.llm_with_tools = None

    async def connect_mcp(self):
        """Connect to MCP GitHub server and discover available tools."""
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

        self.llm_with_tools = self.llm.bind_tools(self._as_langchain_tools())

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
            raise RuntimeError("MCP session not connected. Call connect_mcp() first.")
        result = await self.mcp_session.call_tool(tool_name, tool_input)
        return result.content[0].text if result.content else ""

    async def create_pr_from_error(
        self,
        error_description: str,
        repo: str,
        base_branch: str = "main",
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Main agent loop to create a PR from an error description.

        Args:
            error_description: Description of the error/exception
            repo: Repository in format "owner/repo"
            base_branch: Base branch for the PR (default: "main")
            labels: Optional list of labels to add

        Returns:
            Dictionary with PR details or error information
        """
        print(f"\n🤖 Starting PR creation agent for {repo} [{self.model_name}]...")
        print(f"📝 Error: {error_description[:100]}...")

        system_prompt = """You are a GitHub automation agent. Your job is to:

1. Analyze the error/exception description provided
2. Create a draft Pull Request with:
   - A clear, concise title (under 80 characters) that summarizes the issue
   - A detailed body that includes:
     * Description of the error/exception
     * Potential root cause analysis
     * Proposed fix approach
     * Any relevant context
   - Mark it as a draft PR

Important:
- Use the create_pull_request tool to create the PR
- The PR should be a draft to allow for review before implementation
- Be specific and technical in your analysis
- If you need to check repository details, use available tools

Return a summary of the PR you created with the PR URL."""

        user_message = f"""
Error/Exception to address:
{error_description}

Repository: {repo}
Base Branch: {base_branch}
{f'Labels: {", ".join(labels)}' if labels else ''}

Please create a draft PR to track and address this issue.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        pr_url = None
        max_iterations = 10

        for iteration in range(1, max_iterations + 1):
            print(f"\n🔄 Agent iteration {iteration}...")

            response: AIMessage = await self.llm_with_tools.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                final_text = response.content if isinstance(response.content, str) else str(response.content)
                print("\n✅ Agent completed!")
                return {
                    "status": "success",
                    "message": final_text,
                    "pr_url": pr_url,
                    "iterations": iteration,
                    "model": self.model_name,
                }

            for tool_call in response.tool_calls:
                name = tool_call["name"]
                args = tool_call["args"]
                print(f"  🔧 Executing tool: {name}")
                print(f"     Input: {args}")

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
        }

    async def cleanup(self):
        """Clean up MCP connection."""
        if self.stdio_transport:
            print("🔌 Disconnecting from MCP server...")
            await self.stdio_transport[0].__aexit__(None, None, None)
            print("✅ Disconnected")


async def main():
    """Example usage"""
    from dotenv import load_dotenv
    load_dotenv()

    model = os.getenv("MODEL", "claude-sonnet-4-6")

    agent = GitHubPRAgent(
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        model=model,
    )

    try:
        await agent.connect_mcp()

        result = await agent.create_pr_from_error(
            error_description="""
            NullPointerException in UserService.java:45

            Stack trace:
            java.lang.NullPointerException: Cannot invoke "User.getId()" because "user" is null
                at com.example.UserService.getUserById(UserService.java:45)
                at com.example.UserController.getUser(UserController.java:23)

            Issue: The getUserById() method returns null when a user is not found,
            causing a crash in calling code that doesn't handle null values.

            Proposed fix: Return Optional<User> instead of User to make the
            null case explicit and force calling code to handle it properly.
            """,
            repo="owner/repo",  # Replace with actual repo
            base_branch="main",
        )

        print("\n" + "=" * 60)
        print("RESULT:")
        print(result)

    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
