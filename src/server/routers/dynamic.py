""" This module defines the dynamic router for handling dynamic path requests. """

from typing import Dict, Any
from fastapi import APIRouter, Form, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from server.auth import get_api_key

from server.query_processor import process_query
from server.server_config import templates
from server.server_utils import limiter

router = APIRouter()


@router.get("/{full_path:path}", response_model=None)
async def catch_all(
    request: Request, 
    full_path: str,
    response_type: str = Query("html", description="Response type: 'html' or 'json'"),
    api_key: str = Depends(get_api_key)
):
    """
    Render a page or return JSON with a Git URL based on the provided path.

    This endpoint catches all GET requests with a dynamic path, constructs a Git URL
    using the `full_path` parameter, and either renders the `git.jinja` template or
    returns JSON data based on the response_type parameter.

    Parameters
    ----------
    request : Request
        The incoming request object, which provides context for rendering the response.
    full_path : str
        The full path extracted from the URL, which is used to build the Git URL.
    response_type : str
        The desired response type: 'html' or 'json'.
    api_key : str
        Optional API key for authentication when requesting JSON response.

    Returns
    -------
    HTMLResponse or JSONResponse
        Either an HTML response containing the rendered template, or a JSON response
        containing the Git URL and metadata.
    """
    data = {
        "repo_url": full_path,
        "loading": True,
        "default_file_size": 243,
    }
    
    if response_type == "json":
        if not api_key:
            return JSONResponse(
                status_code=403,
                content={"error": "API key required for JSON responses"}
            )
        return JSONResponse(content=data)
    
    return templates.TemplateResponse(
        "git.jinja",
        {
            "request": request,
            **data
        },
    )


@router.post("/{full_path:path}", response_model=None)
@limiter.limit("10/minute")
async def process_catch_all(
    request: Request,
    input_text: str = Form(...),
    max_file_size: int = Form(...),
    pattern_type: str = Form(...),
    pattern: str = Form(...),
    response_type: str = Query("html", description="Response type: 'html' or 'json'"),
    api_key: str = Depends(get_api_key)
):
    """
    Process the form submission with user input for query parameters.

    This endpoint handles POST requests, processes the input parameters (e.g., text, file size, pattern),
    and calls the `process_query` function to handle the query logic, returning the result as HTML or JSON.

    Parameters
    ----------
    request : Request
        The incoming request object, which provides context for rendering the response.
    input_text : str
        The input text provided by the user for processing, by default taken from the form.
    max_file_size : int
        The maximum allowed file size for the input, specified by the user.
    pattern_type : str
        The type of pattern used for the query, specified by the user.
    pattern : str
        The pattern string used in the query, specified by the user.
    response_type : str
        The desired response type: 'html' or 'json'.
    api_key : str
        Optional API key for authentication when requesting JSON response.

    Returns
    -------
    HTMLResponse or JSONResponse
        Either an HTML response or JSON response after processing the form input and query logic.
    """
    if response_type == "json":
        if not api_key:
            return JSONResponse(
                status_code=403,
                content={"error": "API key required for JSON responses"}
            )
    
    result = await process_query(
        request,
        input_text,
        max_file_size,
        pattern_type,
        pattern,
        is_index=False,
    )
    
    if response_type == "json":
        # Extract data from the HTML response and return as JSON
        if isinstance(result, HTMLResponse):
            return JSONResponse(content={
                "input_text": input_text,
                "max_file_size": max_file_size,
                "pattern_type": pattern_type,
                "pattern": pattern,
                "status": "success"
            })
    
    return result
