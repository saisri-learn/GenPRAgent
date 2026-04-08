"""
GitHub PR Agent using Anthropic SDK and MCP GitHub Server
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitHubPRAgent:
    """Agent that creates GitHub PRs based on error descriptions"""

    def __init__(self, github_token: str, anthropic_api_key: str):
        """
        Initialize the agent

        Args:
            github_token: GitHub personal access token
            anthropic_api_key: Anthropic API key
        """
        self.github_token = github_token
        self.anthropic = Anthropic(api_key=anthropic_api_key)
        self.mcp_session: Optional[ClientSession] = None
        self.stdio_transport = None
        self.available_tools: List[Dict[str, Any]] = []

    async def connect_mcp(self):
        """Connect to MCP GitHub server and discover available tools"""
        print("🔌 Connecting to MCP GitHub server...")

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={
                **os.environ,
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token
            }
        )

        # Start MCP client
        self.stdio_transport = await stdio_client(server_params)
        self.mcp_session = self.stdio_transport[1]

        # Get available tools from MCP server
        tools_response = await self.mcp_session.list_tools()
        self.available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            }
            for tool in tools_response.tools
        ]

        tool_names = [t['name'] for t in self.available_tools]
        print(f"✅ Connected! Available tools: {', '.join(tool_names)}")

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Execute a tool via MCP

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result as string
        """
        if not self.mcp_session:
            raise RuntimeError("MCP session not connected. Call connect_mcp() first.")

        result = await self.mcp_session.call_tool(tool_name, tool_input)
        return result.content[0].text if result.content else ""

    async def create_pr_from_error(
        self,
        error_description: str,
        repo: str,
        base_branch: str = "main",
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main agent loop to create PR from error description

        Args:
            error_description: Description of the error/exception
            repo: Repository in format "owner/repo"
            base_branch: Base branch for the PR (default: "main")
            labels: Optional list of labels to add

        Returns:
            Dictionary with PR details or error information
        """
        print(f"\n🤖 Starting PR creation agent for {repo}...")
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

        messages = [{"role": "user", "content": user_message}]
        pr_url = None

        # Agent loop
        iteration = 0
        max_iterations = 10

        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Agent iteration {iteration}...")

            response = self.anthropic.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_prompt,
                tools=self.available_tools,
                messages=messages
            )

            # Add assistant response to messages
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Check if we're done
            if response.stop_reason == "end_turn":
                # Extract final text response
                final_text = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        final_text += block.text

                print(f"\n✅ Agent completed!")
                return {
                    "status": "success",
                    "message": final_text,
                    "pr_url": pr_url,
                    "iterations": iteration
                }

            # Execute tool calls
            if response.stop_reason == "tool_use":
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  🔧 Executing tool: {block.name}")
                        print(f"     Input: {block.input}")

                        try:
                            # Execute via MCP
                            result = await self.execute_tool(block.name, block.input)
                            print(f"     ✓ Success")

                            # Try to extract PR URL from result
                            if "pull_request" in block.name and "html_url" in result:
                                import json
                                result_data = json.loads(result)
                                pr_url = result_data.get("html_url") or result_data.get("url")

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })
                        except Exception as e:
                            print(f"     ✗ Error: {str(e)}")
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Error executing tool: {str(e)}",
                                "is_error": True
                            })

                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
            else:
                break

        return {
            "status": "error",
            "message": "Max iterations reached",
            "iterations": iteration
        }

    async def cleanup(self):
        """Clean up MCP connection"""
        if self.stdio_transport:
            print("🔌 Disconnecting from MCP server...")
            await self.stdio_transport[0].__aexit__(None, None, None)
            print("✅ Disconnected")


async def main():
    """Example usage"""
    from dotenv import load_dotenv
    load_dotenv()

    agent = GitHubPRAgent(
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
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
            base_branch="main"
        )

        print("\n" + "="*60)
        print("RESULT:")
        print(result)

    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
