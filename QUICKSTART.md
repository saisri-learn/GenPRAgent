# Quick Start Guide - GenPRAgent

Get up and running in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] Node.js installed (for MCP server)
- [ ] GitHub personal access token
- [ ] Anthropic API key

## Step 1: Setup (2 minutes)

```bash
cd GenPRAgent

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install MCP GitHub server
npm install -g @modelcontextprotocol/server-github
```

## Step 2: Configure (1 minute)

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
# - Add GitHub token (from github.com/settings/tokens)
# - Add Anthropic API key (from console.anthropic.com)
```

## Step 3: Test (2 minutes)

### Quick Test

```bash
python test_agent.py
```

Select option 1 and enter your test repository when prompted.

### API Test

Terminal 1:
```bash
python main.py
```

Terminal 2:
```bash
curl -X POST http://localhost:8000/create-pr \
  -H "Content-Type: application/json" \
  -d '{
    "error_description": "TypeError in app.js:123 - Cannot read property of undefined",
    "repo": "yourusername/yourrepo"
  }'
```

## Example Usage

```python
import asyncio
import os
from agent import GitHubPRAgent

async def main():
    agent = GitHubPRAgent(
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    try:
        await agent.connect_mcp()
        
        result = await agent.create_pr_from_error(
            error_description="""
            Database connection timeout in payment processor.
            Error occurs during high load (>1000 concurrent users).
            Need to implement connection pooling.
            """,
            repo="myorg/myapp",
            base_branch="main"
        )
        
        print(f"✅ PR created: {result['pr_url']}")
        
    finally:
        await agent.cleanup()

asyncio.run(main())
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'anthropic'"**
→ Run: `pip install -r requirements.txt`

**"npx: command not found"**
→ Install Node.js from nodejs.org

**"GITHUB_PERSONAL_ACCESS_TOKEN not configured"**
→ Create `.env` file with your credentials

**"Permission denied" on GitHub**
→ Check your token has "Contents" and "Pull Requests" permissions

## Next Steps

- Read full documentation in README.md
- Customize PR templates in agent.py
- Deploy to production (see Dockerfile)
- Integrate with your CI/CD pipeline

## API Quick Reference

```bash
# Health check
curl http://localhost:8000/health

# Create PR (sync)
curl -X POST http://localhost:8000/create-pr \
  -H "Content-Type: application/json" \
  -d '{"error_description": "...", "repo": "owner/repo"}'

# Create PR (async - returns immediately)
curl -X POST http://localhost:8000/create-pr-async \
  -H "Content-Type: application/json" \
  -d '{"error_description": "...", "repo": "owner/repo"}'

# API docs
# Visit: http://localhost:8000/docs
```

## Getting Help

1. Check README.md for detailed documentation
2. Run `python test_agent.py` to diagnose issues
3. Check logs for error messages
4. Verify credentials in .env file

Happy PR generation! 🚀
