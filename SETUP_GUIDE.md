# Complete Setup Guide - GenPRAgent

A detailed step-by-step guide to set up and run GenPRAgent locally.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Python 3.9 or Higher

**Check if Python is installed:**
```bash
python --version
# or
python3 --version
```

**If not installed:**

**Windows:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.11 or 3.12
3. Run the installer
4. ⚠️ **IMPORTANT:** Check "Add Python to PATH" during installation
5. Click "Install Now"
6. Verify installation:
   ```bash
   python --version
   ```

**Mac:**
```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 2. Node.js and npm

**Check if Node.js is installed:**
```bash
node --version
npm --version
```

**If not installed:**

**Windows/Mac:**
1. Go to https://nodejs.org/
2. Download LTS version (recommended)
3. Run installer
4. Verify:
   ```bash
   node --version
   npm --version
   ```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 3. Git

**Check if Git is installed:**
```bash
git --version
```

**If not installed:**
- Windows: https://git-scm.com/download/win
- Mac: `brew install git`
- Linux: `sudo apt install git`

### 4. GitHub Personal Access Token

You need a GitHub token with specific permissions.

**Create GitHub Token:**

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Name it: `GenPRAgent`
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
     - Includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`
   - ✅ `write:discussion` (optional, for discussions)
5. Click "Generate token"
6. **⚠️ IMPORTANT:** Copy the token immediately (starts with `ghp_`)
7. Save it somewhere safe - you won't see it again!

**Token Format:** `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 5. Anthropic API Key

**Get Anthropic API Key:**

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to "API Keys" section
4. Click "Create Key"
5. Name it: `GenPRAgent`
6. Copy the API key (starts with `sk-ant-`)
7. Save it securely

**Key Format:** `sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## Installation

### Step 1: Clone the Repository

```bash
# Clone the repo
git clone https://github.com/saisri-learn/GenPRAgent.git

# Navigate to project directory
cd GenPRAgent

# Verify files
ls
# You should see: agent.py, main.py, requirements.txt, etc.
```

### Step 2: Install MCP GitHub Server

This is the MCP server that provides GitHub tools.

```bash
# Install globally using npm
npm install -g @modelcontextprotocol/server-github

# Verify installation
npx @modelcontextprotocol/server-github --version
```

**Note:** If you get permission errors on Linux/Mac:
```bash
sudo npm install -g @modelcontextprotocol/server-github
```

### Step 3: Set Up Python Virtual Environment

A virtual environment keeps project dependencies isolated.

**Windows:**
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# You should see (venv) in your prompt
```

**Mac/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# You should see (venv) in your prompt
```

**Verify activation:**
```bash
which python  # Should show path inside venv folder
```

### Step 4: Install Python Dependencies

```bash
# Make sure virtual environment is activated (you should see (venv) in prompt)
pip install -r requirements.txt

# This will install:
# - anthropic (Claude API SDK)
# - mcp (Model Context Protocol)
# - fastapi (Web framework)
# - uvicorn (ASGI server)
# - python-dotenv (Environment variables)
```

**Verify installation:**
```bash
pip list
# Should show all installed packages
```

---

## Configuration

### Step 1: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env

# Windows (if cp doesn't work):
copy .env.example .env
```

### Step 2: Edit .env File

Open `.env` in your favorite text editor:

```bash
# Windows
notepad .env

# Mac
open .env

# Linux
nano .env
```

**Add your credentials:**

```env
# GitHub Configuration (REQUIRED)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_actual_token_here

# Anthropic API Configuration (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-your_actual_key_here

# Application Configuration (Optional)
HOST=0.0.0.0
PORT=8000
```

**⚠️ Replace the placeholder values with your actual tokens!**

**Example (with fake tokens):**
```env
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
HOST=0.0.0.0
PORT=8000
```

**Save and close the file.**

### Step 3: Verify Configuration

```bash
# Check that .env exists and has content
cat .env

# Make sure .env is NOT tracked by git (security!)
git status
# .env should NOT appear in the list (it's in .gitignore)
```

---

## Running the Application

You have 3 ways to run the application:

### Option 1: Direct Agent Test (Recommended for First Run)

This runs the agent directly without the API server.

```bash
# Make sure virtual environment is activated
python test_agent.py
```

**What happens:**
1. Menu appears with 3 options
2. Select option `1` (Test Agent Directly)
3. Enter your test repository when prompted: `your-username/your-test-repo`
4. Confirm you want to create a PR
5. Agent will:
   - Connect to MCP GitHub server
   - Send error description to Claude
   - Claude will analyze and create a draft PR
   - PR URL will be displayed

**Example session:**
```
GenPRAgent Test Suite
1. Test Agent Directly
2. Test API Endpoint (requires server running)
3. Exit

Select option (1-3): 1

==============================================================
GenPRAgent Test
==============================================================
🔌 Connecting to MCP GitHub server...
✅ Connected! Available tools: create_pull_request, create_issue, ...

Enter repository (format: owner/repo): saisri-learn/test-repo

⚠️  This will create a draft PR in saisri-learn/test-repo. Continue? (y/n): y

🚀 Creating PR in saisri-learn/test-repo...

🤖 Starting PR creation agent for saisri-learn/test-repo...
📝 Error: NullPointerException in UserService.java:45...

🔄 Agent iteration 1...
  🔧 Executing tool: create_pull_request
     ✓ Success

✅ Agent completed!

==============================================================
RESULT:
==============================================================
Status: success
Message: Created draft PR with detailed error analysis
PR URL: https://github.com/saisri-learn/test-repo/pull/1
Iterations: 2
==============================================================
```

### Option 2: FastAPI Server (For API Access)

Run the REST API server for programmatic access.

**Terminal 1 - Start Server:**
```bash
# Make sure virtual environment is activated
python main.py

# Or use uvicorn directly:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Output:**
```
🚀 Starting GenPRAgent API...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 - Test API:**
```bash
# Health check
curl http://localhost:8000/health

# Create a PR via API
curl -X POST http://localhost:8000/create-pr \
  -H "Content-Type: application/json" \
  -d '{
    "error_description": "TypeError in payment.js line 45: Cannot read property of undefined",
    "repo": "your-username/your-repo",
    "base_branch": "main"
  }'
```

**Or use the API docs UI:**
- Open browser: http://localhost:8000/docs
- Interactive API documentation (Swagger UI)
- Try out endpoints directly in the browser

### Option 3: Python Script

Create your own script:

```python
# my_test.py
import asyncio
import os
from dotenv import load_dotenv
from agent import GitHubPRAgent

async def main():
    load_dotenv()
    
    agent = GitHubPRAgent(
        github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    try:
        await agent.connect_mcp()
        
        result = await agent.create_pr_from_error(
            error_description="""
            Bug Description:
            Application crashes when user clicks 'Submit' button
            without filling required fields.
            
            Error: ValidationError at line 156
            
            Expected: Show validation message
            Actual: Application crashes
            """,
            repo="your-username/your-repo",
            base_branch="main"
        )
        
        print(f"\n✅ Success!")
        print(f"PR URL: {result['pr_url']}")
        print(f"Message: {result['message']}")
        
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python my_test.py
```

---

## Testing

### Quick Health Check

```bash
# Test 1: Check Python and packages
python -c "import anthropic, mcp, fastapi; print('✅ All packages installed')"

# Test 2: Check MCP server
npx @modelcontextprotocol/server-github --help

# Test 3: Check environment variables
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('GitHub Token:', 'SET' if os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN') else 'NOT SET'); print('Anthropic Key:', 'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET')"
```

### Full Integration Test

1. **Create a test repository on GitHub:**
   - Go to https://github.com/new
   - Name: `genpr-test-repo` (or any name)
   - Make it Public or Private (your choice)
   - Click "Create repository"

2. **Run the test script:**
   ```bash
   python test_agent.py
   ```

3. **Select option 1**

4. **Enter your test repo:** `your-username/genpr-test-repo`

5. **Confirm with 'y'**

6. **Check the result:**
   - Should see "✅ Agent completed!"
   - Should show PR URL
   - Open the PR URL in browser
   - Verify the draft PR was created

### Test API Endpoints

If running the FastAPI server:

```bash
# Terminal 1: Start server
python main.py

# Terminal 2: Run tests

# Test 1: Root endpoint
curl http://localhost:8000/

# Test 2: Health check
curl http://localhost:8000/health

# Test 3: Create PR
curl -X POST http://localhost:8000/create-pr \
  -H "Content-Type: application/json" \
  -d '{
    "error_description": "Test error from API",
    "repo": "your-username/your-test-repo"
  }'
```

---

## Troubleshooting

### Issue 1: "python: command not found"

**Problem:** Python not in PATH

**Solution:**
```bash
# Windows: Reinstall Python and check "Add to PATH"
# Or find Python location and add manually

# Mac: Use python3 instead
python3 --version

# Create alias (add to ~/.bashrc or ~/.zshrc)
alias python=python3
```

### Issue 2: "npm: command not found"

**Problem:** Node.js not installed or not in PATH

**Solution:**
- Reinstall Node.js from https://nodejs.org/
- Restart terminal after installation
- Verify: `node --version`

### Issue 3: "ModuleNotFoundError: No module named 'anthropic'"

**Problem:** Packages not installed or wrong Python environment

**Solution:**
```bash
# Make sure virtual environment is activated
# You should see (venv) in prompt

# If not activated:
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# Reinstall packages
pip install -r requirements.txt
```

### Issue 4: "GITHUB_PERSONAL_ACCESS_TOKEN not configured"

**Problem:** Environment variables not loaded

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Check .env content (will show your tokens, be careful!)
cat .env

# Make sure tokens are set correctly (no quotes needed)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_actual_token
ANTHROPIC_API_KEY=sk-ant-actual_key

# Try loading manually
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')[:10] if os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN') else 'NOT SET')"
```

### Issue 5: "Error executing tool: 401 Unauthorized"

**Problem:** Invalid GitHub token or insufficient permissions

**Solution:**
1. Verify token in GitHub settings: https://github.com/settings/tokens
2. Check token has `repo` scope
3. Token might be expired - create new one
4. Update `.env` with new token
5. Restart the application

### Issue 6: "MCP session not connected"

**Problem:** MCP server not running or not installed

**Solution:**
```bash
# Reinstall MCP GitHub server
npm install -g @modelcontextprotocol/server-github

# Verify installation
npx @modelcontextprotocol/server-github --version

# Check Node.js version (should be 18+)
node --version
```

### Issue 7: "Port 8000 already in use"

**Problem:** Another application is using port 8000

**Solution:**

**Option A: Use different port**
```bash
# Edit .env file
PORT=8001

# Or run with custom port
uvicorn main:app --port 8001
```

**Option B: Kill process on port 8000**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:8000 | xargs kill -9
```

### Issue 8: "403 Forbidden" when creating PR

**Problem:** Repository permissions issue

**Solution:**
- Verify you have write access to the repository
- Check repository exists: `https://github.com/owner/repo`
- If private repo, ensure token has access
- Try with a repository you own

### Issue 9: API requests timeout

**Problem:** Claude API or GitHub API taking too long

**Solution:**
- Check internet connection
- Verify API keys are valid
- Claude API might be under load - retry
- Increase timeout in code if needed

### Issue 10: Virtual environment issues

**Problem:** Can't activate venv or packages not found

**Solution:**
```bash
# Delete old venv
rm -rf venv  # Mac/Linux
rmdir /s venv  # Windows

# Create fresh venv
python -m venv venv

# Activate
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate  # Windows

# Reinstall
pip install -r requirements.txt
```

---

## Common Commands Reference

```bash
# Activate virtual environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate  # Windows

# Deactivate virtual environment
deactivate

# Run tests
python test_agent.py

# Start API server
python main.py

# Start with reload (development)
uvicorn main:app --reload

# Check installed packages
pip list

# Update packages
pip install --upgrade -r requirements.txt

# View logs
# Logs appear in terminal where you run the app
```

---

## Next Steps

Once everything is working:

1. **Read the full README.md** for advanced features
2. **Check QUICKSTART.md** for quick examples
3. **Try multi-MCP setup** (if you added those files)
4. **Customize the agent** in `agent.py`
5. **Deploy to production** using Docker (see Dockerfile)

---

## Getting Help

**Resources:**
- Project README: [README.md](README.md)
- Quick Start: [QUICKSTART.md](QUICKSTART.md)
- GitHub Issues: https://github.com/saisri-learn/GenPRAgent/issues
- MCP Documentation: https://modelcontextprotocol.io
- Anthropic Docs: https://docs.anthropic.com

**Common Questions:**

**Q: Can I use this without Docker?**
A: Yes! This guide shows how to run locally without Docker.

**Q: Do I need Slack/Filesystem/other MCPs?**
A: No, only GitHub MCP is required. Others are optional.

**Q: Can I use this in production?**
A: Yes, but consider security (secrets management), scaling, and error handling.

**Q: How much does it cost?**
A: Depends on Claude API usage. Check Anthropic pricing: https://www.anthropic.com/pricing

**Q: Can I customize the PR format?**
A: Yes! Edit the `system_prompt` in `agent.py`

---

## Success Checklist

- [ ] Python 3.9+ installed
- [ ] Node.js and npm installed
- [ ] GitHub token created with `repo` scope
- [ ] Anthropic API key obtained
- [ ] Repository cloned
- [ ] MCP GitHub server installed
- [ ] Virtual environment created and activated
- [ ] Python packages installed
- [ ] .env file configured with tokens
- [ ] Test script runs successfully
- [ ] Draft PR created in test repository

**If all checked, you're ready to use GenPRAgent! 🎉**

---

*Last Updated: April 2026*
*GenPRAgent v1.0.0*
