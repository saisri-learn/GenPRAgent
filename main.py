"""
FastAPI server for GitHub PR Agent
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import os
from dotenv import load_dotenv
import asyncio
from contextlib import asynccontextmanager

from agent import GitHubPRAgent

# Load environment variables
load_dotenv()

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting GenPRAgent API...")
    yield
    print("👋 Shutting down GenPRAgent API...")

app = FastAPI(
    title="GenPRAgent API",
    description="AI-powered GitHub PR creation from error descriptions",
    version="1.0.0",
    lifespan=lifespan
)


class ErrorRequest(BaseModel):
    """Request model for creating a PR from an error"""
    error_description: str = Field(
        ...,
        description="Detailed description of the error/exception",
        min_length=10
    )
    repo: str = Field(
        ...,
        description="GitHub repository in format 'owner/repo'",
        pattern=r"^[\w\-\.]+/[\w\-\.]+$"
    )
    base_branch: str = Field(
        default="main",
        description="Base branch for the PR"
    )
    labels: Optional[List[str]] = Field(
        default=None,
        description="Optional labels to add to the PR"
    )


class ErrorResponse(BaseModel):
    """Response model for PR creation"""
    status: str
    message: str
    pr_url: Optional[str] = None
    iterations: Optional[int] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "GenPRAgent",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    return {
        "status": "healthy",
        "github_configured": bool(github_token),
        "anthropic_configured": bool(anthropic_key)
    }


@app.post("/create-pr", response_model=ErrorResponse)
async def create_pr_endpoint(request: ErrorRequest):
    """
    Create a GitHub PR from an error description

    This endpoint:
    1. Takes an error/exception description
    2. Uses Claude AI to analyze it
    3. Creates a draft PR with detailed information

    Returns the PR URL and details
    """
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not github_token:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_PERSONAL_ACCESS_TOKEN not configured"
        )

    if not anthropic_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured"
        )

    agent = GitHubPRAgent(
        github_token=github_token,
        anthropic_api_key=anthropic_key
    )

    try:
        await agent.connect_mcp()

        result = await agent.create_pr_from_error(
            error_description=request.error_description,
            repo=request.repo,
            base_branch=request.base_branch,
            labels=request.labels
        )

        if result["status"] == "success":
            return ErrorResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    finally:
        await agent.cleanup()


@app.post("/create-pr-async")
async def create_pr_async_endpoint(request: ErrorRequest, background_tasks: BackgroundTasks):
    """
    Create a GitHub PR asynchronously (returns immediately)

    Use this endpoint for long-running PR creation tasks.
    The actual PR creation happens in the background.
    """
    async def create_pr_task():
        agent = GitHubPRAgent(
            github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        try:
            await agent.connect_mcp()
            await agent.create_pr_from_error(
                error_description=request.error_description,
                repo=request.repo,
                base_branch=request.base_branch,
                labels=request.labels
            )
        finally:
            await agent.cleanup()

    background_tasks.add_task(create_pr_task)

    return {
        "status": "accepted",
        "message": "PR creation task started in background"
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(app, host=host, port=port)
