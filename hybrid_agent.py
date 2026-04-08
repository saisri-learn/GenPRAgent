"""
Hybrid Multi-LLM Agent for GitHub PR Generation
Supports: GPT-4o mini (testing/simple), Claude Sonnet (complex)
"""
import os
import asyncio
import json
from typing import List, Dict, Any, Optional, Literal
from anthropic import Anthropic
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


LLMProvider = Literal["gpt-4o-mini", "gpt-4o", "claude-sonnet", "claude-haiku", "auto"]


class HybridPRAgent:
    """
    Hybrid agent that can use multiple LLMs intelligently
    - GPT-4o mini: Fast, cheap, good for testing and simple errors
    - Claude Sonnet: Best quality, for complex errors
    - Auto mode: Analyzes complexity and chooses best LLM
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        github_token: Optional[str] = None,
        default_llm: LLMProvider = "gpt-4o-mini"
    ):
        """
        Initialize hybrid agent

        Args:
            openai_api_key: OpenAI API key (for GPT models)
            anthropic_api_key: Anthropic API key (for Claude models)
            github_token: GitHub personal access token
            default_llm: Default LLM to use
        """
        self.openai = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.anthropic = Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None
        self.github_token = github_token
        self.default_llm = default_llm

        self.mcp_session: Optional[ClientSession] = None
        self.stdio_transport = None
        self.available_tools: List[Dict[str, Any]] = []

        # Cost tracking
        self.total_cost = 0.0
        self.llm_usage = {}

    async def connect_mcp(self):
        """Connect to MCP GitHub server"""
        print("🔌 Connecting to MCP GitHub server...")

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={
                **os.environ,
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token
            }
        )

        self.stdio_transport = await stdio_client(server_params)
        self.mcp_session = self.stdio_transport[1]

        # Get available tools
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
        """Execute tool via MCP"""
        if not self.mcp_session:
            raise RuntimeError("MCP session not connected")

        result = await self.mcp_session.call_tool(tool_name, tool_input)
        return result.content[0].text if result.content else ""

    def _analyze_complexity(self, error_description: str) -> Literal["simple", "complex"]:
        """
        Analyze error complexity to choose appropriate LLM

        Simple: Single error, clear stack trace, common issue
        Complex: Multiple errors, unclear root cause, architectural issue
        """
        description_lower = error_description.lower()

        # Indicators of complexity
        complex_indicators = [
            "architecture", "design", "refactor", "migrate",
            "multiple", "concurrent", "race condition", "deadlock",
            "performance", "scale", "optimize", "memory leak",
            "security", "vulnerability", "injection",
            len(error_description) > 1000,  # Long descriptions
            error_description.count("\n") > 30,  # Many lines
        ]

        simple_indicators = [
            "nullpointer", "undefined", "typeerror",
            "syntax error", "import error", "not found",
            "missing", "typo"
        ]

        complexity_score = 0

        for indicator in complex_indicators:
            if isinstance(indicator, bool):
                if indicator:
                    complexity_score += 1
            elif indicator in description_lower:
                complexity_score += 1

        for indicator in simple_indicators:
            if indicator in description_lower:
                complexity_score -= 1

        return "complex" if complexity_score > 1 else "simple"

    def _convert_tools_to_openai_format(self) -> List[Dict]:
        """Convert MCP tools to OpenAI function format"""
        openai_tools = []
        for tool in self.available_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })
        return openai_tools

    def _estimate_cost(self, llm: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token usage"""
        pricing = {
            "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
            "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
            "claude-sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
            "claude-haiku": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
        }

        if llm not in pricing:
            return 0.0

        cost = (input_tokens * pricing[llm]["input"]) + (output_tokens * pricing[llm]["output"])
        return cost

    async def _call_gpt(
        self,
        messages: List[Dict],
        system_prompt: str,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """Call OpenAI GPT model"""
        if not self.openai:
            raise RuntimeError("OpenAI API key not configured")

        # Add system message
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        response = self.openai.chat.completions.create(
            model=model,
            messages=full_messages,
            tools=self._convert_tools_to_openai_format(),
            tool_choice="auto"
        )

        # Track usage
        usage = response.usage
        cost = self._estimate_cost(model, usage.prompt_tokens, usage.completion_tokens)
        self.total_cost += cost
        self.llm_usage[model] = self.llm_usage.get(model, 0) + 1

        return {
            "content": response.choices[0].message,
            "stop_reason": "tool_calls" if response.choices[0].message.tool_calls else "end_turn",
            "usage": {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "cost": cost
            }
        }

    async def _call_claude(
        self,
        messages: List[Dict],
        system_prompt: str,
        model: str = "claude-sonnet-4-6"
    ) -> Dict[str, Any]:
        """Call Anthropic Claude model"""
        if not self.anthropic:
            raise RuntimeError("Anthropic API key not configured")

        response = self.anthropic.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            tools=self.available_tools,
            messages=messages
        )

        # Track usage
        usage = response.usage
        llm_name = "claude-sonnet" if "sonnet" in model else "claude-haiku"
        cost = self._estimate_cost(llm_name, usage.input_tokens, usage.output_tokens)
        self.total_cost += cost
        self.llm_usage[llm_name] = self.llm_usage.get(llm_name, 0) + 1

        return {
            "content": response.content,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cost": cost
            }
        }

    async def create_pr_from_error(
        self,
        error_description: str,
        repo: str,
        base_branch: str = "main",
        llm: LLMProvider = None
    ) -> Dict[str, Any]:
        """
        Create PR using hybrid LLM approach

        Args:
            error_description: Error/exception description
            repo: Repository (owner/repo)
            base_branch: Base branch
            llm: LLM to use (None = use default)

        Returns:
            Result dict with PR details and cost info
        """
        # Determine which LLM to use
        if llm is None:
            llm = self.default_llm

        if llm == "auto":
            complexity = self._analyze_complexity(error_description)
            llm = "claude-sonnet" if complexity == "complex" else "gpt-4o-mini"
            print(f"🤖 Auto-detected complexity: {complexity}")
            print(f"📊 Selecting LLM: {llm}")

        print(f"\n🚀 Starting PR creation with {llm.upper()}...")
        print(f"📝 Error: {error_description[:100]}...")

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

        # Initialize conversation
        if llm.startswith("gpt"):
            messages = [{"role": "user", "content": user_message}]
        else:
            messages = [{"role": "user", "content": user_message}]

        pr_url = None
        iteration = 0
        max_iterations = 10

        # Agent loop
        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration} [{llm}]...")

            # Call appropriate LLM
            if llm.startswith("gpt"):
                response = await self._call_gpt(messages, system_prompt, model=llm)
                msg_content = response["content"]

                # Handle GPT response
                if msg_content.tool_calls:
                    # Add assistant message
                    messages.append({
                        "role": "assistant",
                        "content": msg_content.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in msg_content.tool_calls
                        ]
                    })

                    # Execute tools
                    for tool_call in msg_content.tool_calls:
                        print(f"  🔧 {tool_call.function.name}")

                        try:
                            args = json.loads(tool_call.function.arguments)
                            result = await self.execute_tool(tool_call.function.name, args)
                            print(f"     ✓ Success")

                            # Track PR URL
                            if "pull_request" in tool_call.function.name and "html_url" in result:
                                result_data = json.loads(result)
                                pr_url = result_data.get("html_url") or result_data.get("url")

                            # Add tool result
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": result
                            })
                        except Exception as e:
                            print(f"     ✗ Error: {e}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: {str(e)}"
                            })
                else:
                    # Done
                    final_text = msg_content.content or "Completed"
                    print(f"\n✅ Agent completed!")
                    return {
                        "status": "success",
                        "message": final_text,
                        "pr_url": pr_url,
                        "llm_used": llm,
                        "iterations": iteration,
                        "total_cost": self.total_cost,
                        "cost_usd": f"${self.total_cost:.6f}"
                    }

            else:  # Claude
                response = await self._call_claude(messages, system_prompt, model=llm)

                # Add assistant message
                messages.append({
                    "role": "assistant",
                    "content": response["content"]
                })

                if response["stop_reason"] == "end_turn":
                    final_text = ""
                    for block in response["content"]:
                        if hasattr(block, 'text'):
                            final_text += block.text

                    print(f"\n✅ Agent completed!")
                    return {
                        "status": "success",
                        "message": final_text,
                        "pr_url": pr_url,
                        "llm_used": llm,
                        "iterations": iteration,
                        "total_cost": self.total_cost,
                        "cost_usd": f"${self.total_cost:.6f}"
                    }

                # Execute tool calls
                if response["stop_reason"] == "tool_use":
                    tool_results = []

                    for block in response["content"]:
                        if block.type == "tool_use":
                            print(f"  🔧 {block.name}")

                            try:
                                result = await self.execute_tool(block.name, block.input)
                                print(f"     ✓ Success")

                                # Track PR URL
                                if "pull_request" in block.name and "html_url" in result:
                                    result_data = json.loads(result)
                                    pr_url = result_data.get("html_url") or result_data.get("url")

                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result
                                })
                            except Exception as e:
                                print(f"     ✗ Error: {e}")
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": f"Error: {str(e)}",
                                    "is_error": True
                                })

                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })

        return {
            "status": "error",
            "message": "Max iterations reached",
            "iterations": iteration,
            "total_cost": self.total_cost
        }

    async def cleanup(self):
        """Clean up MCP connection"""
        if self.stdio_transport:
            print("🔌 Disconnecting from MCP server...")
            await self.stdio_transport[0].__aexit__(None, None, None)
            print("✅ Disconnected")

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary"""
        return {
            "total_cost_usd": f"${self.total_cost:.6f}",
            "llm_usage": self.llm_usage,
            "average_cost_per_call": f"${self.total_cost / max(sum(self.llm_usage.values()), 1):.6f}"
        }


async def main():
    """Example usage"""
    from dotenv import load_dotenv
    load_dotenv()

    print("="*60)
    print("Hybrid Multi-LLM PR Agent")
    print("="*60)

    print("\nSelect LLM:")
    print("1. GPT-4o mini (fast, cheap - $0.001/PR)")
    print("2. Claude Sonnet (best quality - $0.03/PR)")
    print("3. Auto (analyzes complexity)")

    choice = input("\nChoice (1-3): ").strip()

    llm_map = {
        "1": "gpt-4o-mini",
        "2": "claude-sonnet",
        "3": "auto"
    }

    selected_llm = llm_map.get(choice, "gpt-4o-mini")

    agent = HybridPRAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        default_llm=selected_llm
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
            repo=repo
        )

        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        print(f"Status: {result['status']}")
        print(f"LLM Used: {result.get('llm_used', 'N/A')}")
        print(f"Cost: {result.get('cost_usd', 'N/A')}")
        print(f"PR URL: {result.get('pr_url', 'N/A')}")
        print(f"Message: {result['message'][:200]}...")
        print("="*60)

        # Show cost summary
        cost_summary = agent.get_cost_summary()
        print("\n💰 Cost Summary:")
        print(f"Total Cost: {cost_summary['total_cost_usd']}")
        print(f"LLM Usage: {cost_summary['llm_usage']}")

    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
