"""
Test script for Hybrid Multi-LLM Agent
"""
import asyncio
import os
from dotenv import load_dotenv
from hybrid_agent import HybridPRAgent


async def test_gpt_4o_mini():
    """Test with GPT-4o mini (cheapest, fastest)"""
    print("\n" + "="*60)
    print("Test 1: GPT-4o mini")
    print("="*60)

    load_dotenv()

    agent = HybridPRAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        default_llm="gpt-4o-mini"
    )

    try:
        await agent.connect_mcp()

        repo = input("\nEnter test repository (owner/repo): ").strip()
        if not repo or "/" not in repo:
            print("❌ Invalid repository format")
            return

        confirm = input(f"⚠️  Create draft PR in {repo}? (y/n): ")
        if confirm.lower() != 'y':
            print("Test cancelled")
            return

        result = await agent.create_pr_from_error(
            error_description="""
            TypeError in payment_processor.py line 156

            Error: Cannot read property 'amount' of undefined

            Steps to reproduce:
            1. Submit payment form without amount field
            2. Application crashes

            Expected: Validation error message
            Actual: Uncaught TypeError

            Impact: Payment processing broken for users
            """,
            repo=repo,
            llm="gpt-4o-mini"
        )

        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        print(f"✅ Status: {result['status']}")
        print(f"🤖 LLM: {result.get('llm_used')}")
        print(f"💰 Cost: {result.get('cost_usd')}")
        print(f"🔗 PR: {result.get('pr_url')}")
        print(f"📊 Iterations: {result.get('iterations')}")

        # Cost summary
        cost_summary = agent.get_cost_summary()
        print("\n💰 Total Session Cost:")
        print(f"   {cost_summary['total_cost_usd']}")

    finally:
        await agent.cleanup()


async def test_claude_sonnet():
    """Test with Claude Sonnet (best quality)"""
    print("\n" + "="*60)
    print("Test 2: Claude Sonnet")
    print("="*60)

    load_dotenv()

    agent = HybridPRAgent(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        default_llm="claude-sonnet"
    )

    try:
        await agent.connect_mcp()

        repo = input("\nEnter test repository (owner/repo): ").strip()
        if not repo or "/" not in repo:
            print("❌ Invalid repository format")
            return

        confirm = input(f"⚠️  Create draft PR in {repo}? (y/n): ")
        if confirm.lower() != 'y':
            print("Test cancelled")
            return

        result = await agent.create_pr_from_error(
            error_description="""
            Performance Degradation in User Authentication System

            Issue: Login API response time increased from 200ms to 5000ms
            after deploying v2.3.0.

            Analysis:
            - Database queries increased from 2 to 15 per login
            - N+1 query problem in user permissions check
            - No caching layer for frequently accessed user data

            Impact:
            - 80% of users experiencing slow logins
            - Support tickets increased 300%
            - Risk of users abandoning platform

            This is a complex architectural issue requiring careful analysis.
            """,
            repo=repo,
            llm="claude-sonnet"
        )

        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        print(f"✅ Status: {result['status']}")
        print(f"🤖 LLM: {result.get('llm_used')}")
        print(f"💰 Cost: {result.get('cost_usd')}")
        print(f"🔗 PR: {result.get('pr_url')}")
        print(f"📊 Iterations: {result.get('iterations')}")

        # Cost summary
        cost_summary = agent.get_cost_summary()
        print("\n💰 Total Session Cost:")
        print(f"   {cost_summary['total_cost_usd']}")

    finally:
        await agent.cleanup()


async def test_auto_mode():
    """Test with auto mode (intelligent selection)"""
    print("\n" + "="*60)
    print("Test 3: Auto Mode (Intelligent LLM Selection)")
    print("="*60)

    load_dotenv()

    agent = HybridPRAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        default_llm="auto"
    )

    try:
        await agent.connect_mcp()

        repo = input("\nEnter test repository (owner/repo): ").strip()
        if not repo or "/" not in repo:
            print("❌ Invalid repository format")
            return

        # Test 1: Simple error (should use GPT-4o mini)
        print("\n📝 Test 3a: Simple Error")
        print("   Expected: GPT-4o mini")

        result1 = await agent.create_pr_from_error(
            error_description="NullPointerException in UserService.java:45",
            repo=repo,
            llm="auto"
        )
        print(f"   ✅ Used: {result1.get('llm_used')} | Cost: {result1.get('cost_usd')}")

        # Test 2: Complex error (should use Claude Sonnet)
        print("\n📝 Test 3b: Complex Error")
        print("   Expected: Claude Sonnet")

        result2 = await agent.create_pr_from_error(
            error_description="""
            Critical security vulnerability in authentication system.
            Multiple issues: SQL injection risk, password not hashed,
            session tokens stored in plain text. Requires architectural
            refactoring and careful migration strategy.
            """,
            repo=repo,
            llm="auto"
        )
        print(f"   ✅ Used: {result2.get('llm_used')} | Cost: {result2.get('cost_usd')}")

        # Summary
        cost_summary = agent.get_cost_summary()
        print("\n" + "="*60)
        print("AUTO MODE SUMMARY:")
        print("="*60)
        print(f"Total Cost: {cost_summary['total_cost_usd']}")
        print(f"LLM Usage: {cost_summary['llm_usage']}")
        print("="*60)

    finally:
        await agent.cleanup()


async def compare_all():
    """Compare all LLMs side by side"""
    print("\n" + "="*60)
    print("Test 4: Compare All LLMs")
    print("="*60)

    load_dotenv()

    repo = input("\nEnter test repository (owner/repo): ").strip()
    if not repo or "/" not in repo:
        print("❌ Invalid repository format")
        return

    confirm = input(f"⚠️  This will create 2 PRs in {repo}. Continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Test cancelled")
        return

    error_description = """
    Bug in data processing pipeline

    Error: IndexError at line 234 in data_processor.py
    List index out of range when processing empty datasets

    Expected: Handle empty datasets gracefully
    Actual: Application crashes
    """

    results = {}

    # Test GPT-4o mini
    print("\n🧪 Testing GPT-4o mini...")
    agent_gpt = HybridPRAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    )
    try:
        await agent_gpt.connect_mcp()
        results['gpt-4o-mini'] = await agent_gpt.create_pr_from_error(
            error_description=error_description,
            repo=repo,
            llm="gpt-4o-mini"
        )
    finally:
        await agent_gpt.cleanup()

    # Test Claude Sonnet
    print("\n🧪 Testing Claude Sonnet...")
    agent_claude = HybridPRAgent(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    )
    try:
        await agent_claude.connect_mcp()
        results['claude-sonnet'] = await agent_claude.create_pr_from_error(
            error_description=error_description,
            repo=repo,
            llm="claude-sonnet"
        )
    finally:
        await agent_claude.cleanup()

    # Display comparison
    print("\n" + "="*60)
    print("COMPARISON RESULTS:")
    print("="*60)

    for llm, result in results.items():
        print(f"\n{llm.upper()}:")
        print(f"  Status: {result['status']}")
        print(f"  Cost: {result.get('cost_usd', 'N/A')}")
        print(f"  Iterations: {result.get('iterations', 'N/A')}")
        print(f"  PR URL: {result.get('pr_url', 'N/A')}")

    # Cost comparison
    gpt_cost = float(results['gpt-4o-mini'].get('cost_usd', '$0').replace('$', ''))
    claude_cost = float(results['claude-sonnet'].get('cost_usd', '$0').replace('$', ''))

    print("\n💰 COST ANALYSIS:")
    print(f"  GPT-4o mini: ${gpt_cost:.6f}")
    print(f"  Claude Sonnet: ${claude_cost:.6f}")
    print(f"  Savings with GPT: ${(claude_cost - gpt_cost):.6f} ({((claude_cost - gpt_cost) / claude_cost * 100):.1f}%)")


def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("Hybrid Multi-LLM Agent - Test Suite")
    print("="*60)

    print("\nAvailable Tests:")
    print("1. Test GPT-4o mini (fast, cheap)")
    print("2. Test Claude Sonnet (best quality)")
    print("3. Test Auto Mode (intelligent selection)")
    print("4. Compare All LLMs")
    print("5. Exit")

    choice = input("\nSelect test (1-5): ").strip()

    if choice == "1":
        asyncio.run(test_gpt_4o_mini())
    elif choice == "2":
        asyncio.run(test_claude_sonnet())
    elif choice == "3":
        asyncio.run(test_auto_mode())
    elif choice == "4":
        asyncio.run(compare_all())
    elif choice == "5":
        print("Exiting...")
    else:
        print("Invalid option")


if __name__ == "__main__":
    main()
