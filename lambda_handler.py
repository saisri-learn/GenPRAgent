"""
AWS Lambda handler for GenPRAgent
Wraps FastAPI with Mangum for Lambda compatibility
"""
import os
from mangum import Mangum
from main import app

# Wrap FastAPI app with Mangum for Lambda
handler = Mangum(app, lifespan="off")

# Lambda function handler
def lambda_handler(event, context):
    """
    AWS Lambda handler function

    Args:
        event: Lambda event (from API Gateway)
        context: Lambda context

    Returns:
        Response dict for API Gateway
    """
    return handler(event, context)
