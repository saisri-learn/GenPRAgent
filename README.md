# GenPRAgent - AI-Powered GitHub PR Generator

An intelligent agent that automatically creates GitHub Pull Requests from error/exception descriptions using Claude AI and the Model Context Protocol (MCP).

## Architecture

```
User Request → FastAPI → Agent (Anthropic SDK)
                           ↓
                    Claude AI (analyzes error)
                           ↓
                    MCP Client → MCP GitHub Server → GitHub API
                           ↓
                    Draft PR Created
```

## Features

- 🤖 **AI-Powered Analysis**: Uses Claude Sonnet 4.6 to analyze errors and create detailed PR descriptions
- 🔧 **MCP Integration**: Leverages Model Context Protocol for GitHub operations
- 🚀 **REST API**: FastAPI endpoint for easy integration
- 📝 **Draft PRs**: Creates draft PRs with detailed error analysis and proposed solutions
- ⚡ **Async Support**: Background task processing for long-running operations

## Prerequisites

1. **Node.js** (for MCP GitHub server)
   - Download from https://nodejs.org/

2. **Python 3.9+**

3. **GitHub Personal Access Token**
   - Go to: Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Permissions needed:
     - Contents: Read and Write
     - Pull requests: Read and Write
     - Issues: Read and Write (optional)

4. **Anthropic API Key**
   - Get from: https://console.anthropic.com/

## Installation

### 1. Clone or navigate to the project

```bash
cd GenPRAgent
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install MCP GitHub Server

```bash
npm install -g @modelcontextprotocol/server-github
```

### 5. Configure environment variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your credentials
```

Example `.env`:
```env
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
HOST=0.0.0.0
PORT=8000
```

## Usage

### Option 1: Direct Agent Usage

Run the agent directly with the test script:

```bash
python test_agent.py
```

Select option 1 and follow the prompts.

### Option 2: FastAPI Server

1. Start the server:

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Test the API:

```bash
curl -X POST http://localhost:8000/create-pr \
  -H "Content-Type: application/json" \
  -d '{
    "error_description": "NullPointerException in UserService.java:45...",
    "repo": "owner/repo",
    "base_branch": "main"
  }'
```

3. View API docs:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Option 3: Python Code

```python
import asyncio
from agent import GitHubPRAgent
import os

async def main():
    agent = GitHubPRAgent(
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    try:
        await agent.connect_mcp()
        
        result = await agent.create_pr_from_error(
            error_description="Your error description here...",
            repo="owner/repo",
            base_branch="main"
        )
        
        print(f"PR URL: {result['pr_url']}")
        
    finally:
        await agent.cleanup()

asyncio.run(main())
```

## API Endpoints

### `POST /create-pr`

Create a GitHub PR from an error description (synchronous).

**Request Body:**
```json
{
  "error_description": "Detailed error description...",
  "repo": "owner/repo",
  "base_branch": "main",
  "labels": ["bug", "high-priority"]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Created draft PR #123...",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "iterations": 3
}
```

### `POST /create-pr-async`

Create a PR asynchronously (returns immediately).

### `GET /health`

Health check endpoint.

## Example Error Descriptions

The agent works best with detailed error descriptions:

```
NullPointerException in UserService.java:45

Stack trace:
java.lang.NullPointerException: Cannot invoke "User.getId()" because "user" is null
    at com.example.UserService.getUserById(UserService.java:45)

Issue: getUserById() returns null when user not found
Impact: API returns 500 errors instead of 404
Proposed fix: Return Optional<User> instead of User
```

## Project Structure

```
GenPRAgent/
├── agent.py              # Main agent logic with MCP integration
├── main.py              # FastAPI server
├── test_agent.py        # Test scripts
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Your credentials (not in git)
├── README.md            # This file
├── Dockerfile           # Container configuration
└── .gitignore          # Git ignore rules
```

## Deployment

### Docker

```bash
# Build image
docker build -t genpr-agent .

# Run container
docker run -d \
  -p 8000:8000 \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=xxx \
  -e ANTHROPIC_API_KEY=xxx \
  --name genpr-agent \
  genpr-agent
```

### AWS ECS / Cloud Run

The application is designed for container-based deployment:
- Uses long-running processes (MCP server)
- Handles async operations
- Suitable for ECS, Cloud Run, or Kubernetes

See Dockerfile for containerization details.

## Troubleshooting

### "MCP session not connected"
- Ensure Node.js is installed
- Verify `npx` is in your PATH
- Check GitHub token permissions

### "GITHUB_PERSONAL_ACCESS_TOKEN not configured"
- Copy `.env.example` to `.env`
- Add your GitHub token to `.env`

### "Rate limit exceeded"
- GitHub API has rate limits
- Wait a few minutes and retry
- Consider using a GitHub App instead of PAT for higher limits

### Tool execution errors
- Check GitHub token has correct permissions
- Verify repository exists and you have access
- Check repository name format is "owner/repo"

## How It Works

1. **User submits error description** via API or direct agent call
2. **Agent connects to MCP** GitHub server
3. **Claude AI analyzes** the error description
4. **Claude decides** which GitHub tools to use (via MCP)
5. **Agent executes** tool calls through MCP client
6. **MCP GitHub server** makes actual GitHub API calls
7. **Draft PR created** with detailed analysis
8. **Results returned** to user with PR URL

## Available MCP GitHub Tools

The agent has access to these GitHub operations:
- `create_pull_request` - Create PRs
- `create_or_update_file` - Modify files
- `create_issue` - Create issues
- `search_code` - Search code
- `get_file_contents` - Read files
- `list_repositories` - List repos
- And more...

## Future Enhancements

- [ ] Automatic code fix suggestions
- [ ] Multi-repository support
- [ ] Custom PR templates
- [ ] Integration with issue trackers
- [ ] Slack/Discord notifications
- [ ] PR quality scoring
- [ ] Automatic code analysis

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use in your projects!

## Support

For issues or questions:
- Open a GitHub issue
- Check the troubleshooting section
- Review MCP documentation: https://modelcontextprotocol.io

---

Built with ❤️ using Claude AI and MCP
