"""Authentication module for API key validation."""

import os
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

# API key configuration
API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate the API key from the request header.
    
    Parameters
    ----------
    api_key_header : str
        The API key from the request header
        
    Returns
    -------
    str
        The validated API key
        
    Raises
    ------
    HTTPException
        If the API key is invalid
    """
    if not API_KEY:
        return None
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=403,
        detail="Invalid API key"
    )
