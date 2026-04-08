"""
Test script for the GitHub PR Agent
"""
import asyncio
import os
from dotenv import load_dotenv
from agent import GitHubPRAgent


async def test_basic():
    """Basic test of the PR agent"""
    load_dotenv()

    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not github_token:
        print("❌ GITHUB_PERSONAL_ACCESS_TOKEN not set in .env")
        return

    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY not set in .env")
        return

    print("="*60)
    print("GenPRAgent Test")
    print("="*60)

    agent = GitHubPRAgent(
        github_token=github_token,
        anthropic_api_key=anthropic_key
    )

    try:
        await agent.connect_mcp()

        # Example error description
        error_description = """
        NullPointerException in UserService.java:45

        Stack trace:
        java.lang.NullPointerException: Cannot invoke "User.getId()" because "user" is null
            at com.example.UserService.getUserById(UserService.java:45)
            at com.example.UserController.getUser(UserController.java:23)

        Issue Description:
        The getUserById() method returns null when a user is not found in the database,
        causing a NullPointerException in calling code that doesn't handle null values.

        Impact:
        - API returns 500 errors instead of proper 404 responses
        - Application crashes when non-existent user IDs are queried
        - Poor user experience and error handling

        Proposed Solution:
        1. Return Optional<User> instead of User to make the null case explicit
        2. Update calling code to handle Optional properly
        3. Return proper HTTP 404 responses when user not found
        4. Add unit tests to prevent regression
        """

        # TODO: Replace with your actual repository
        test_repo = input("\nEnter repository (format: owner/repo): ").strip()

        if not test_repo or "/" not in test_repo:
            print("❌ Invalid repository format")
            return

        confirm = input(f"\n⚠️  This will create a draft PR in {test_repo}. Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Test cancelled")
            return

        print(f"\n🚀 Creating PR in {test_repo}...")

        result = await agent.create_pr_from_error(
            error_description=error_description,
            repo=test_repo,
            base_branch="main"
        )

        print("\n" + "="*60)
        print("TEST RESULT:")
        print("="*60)
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        if result.get('pr_url'):
            print(f"PR URL: {result['pr_url']}")
        print(f"Iterations: {result.get('iterations', 'N/A')}")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await agent.cleanup()


async def test_api_endpoint():
    """Test the FastAPI endpoint"""
    import httpx

    print("\n" + "="*60)
    print("Testing API Endpoint")
    print("="*60)

    url = "http://localhost:8000/create-pr"

    payload = {
        "error_description": """
        TypeError: Cannot read property 'map' of undefined
        at components/UserList.jsx:23

        The users array is undefined when the API call fails,
        causing a crash when trying to map over it.

        Need to add proper error handling and loading states.
        """,
        "repo": "owner/repo",  # Replace with actual repo
        "base_branch": "main"
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"\nSending POST request to {url}...")
            response = await client.post(url, json=payload)

            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")

    except httpx.ConnectError:
        print("❌ Could not connect to API. Is the server running?")
        print("   Start it with: python main.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Main test menu"""
    print("\nGenPRAgent Test Suite")
    print("1. Test Agent Directly")
    print("2. Test API Endpoint (requires server running)")
    print("3. Exit")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == "1":
        asyncio.run(test_basic())
    elif choice == "2":
        asyncio.run(test_api_endpoint())
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid option")


if __name__ == "__main__":
    main()
