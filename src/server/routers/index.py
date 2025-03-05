""" This module defines the index router for handling the home page and its functionality. """

from fastapi import APIRouter, Form, Request, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from server.auth import get_api_key

from server.query_processor import process_query, parse_query, ingest_query, clone_repo
from server.server_config import templates, EXAMPLE_REPOS
from server.server_utils import limiter, log_slider_to_size

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """
    Render the home page with example repositories and default parameters.

    This endpoint serves the home page of the application, rendering the `index.jinja` template
    and providing it with a list of example repositories and default file size values.

    Parameters
    ----------
    request : Request
        The incoming request object, which provides context for rendering the response.

    Returns
    -------
    HTMLResponse
        An HTML response containing the rendered home page template, with example repositories
        and other default parameters such as file size.
    """
    return templates.TemplateResponse(
        "index.jinja",
        {
            "request": request,
            "examples": EXAMPLE_REPOS,
            "default_file_size": 243,
        },
    )


@router.post("/", response_model=None)
@limiter.limit("10/minute")
async def index_post(
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

    This endpoint handles POST requests from the home page form. It processes the user-submitted
    input (e.g., text, file size, pattern type) and invokes the `process_query` function to handle
    the query logic, returning the result as HTML or JSON response.

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
        Either an HTML response containing the results of processing the form input and query logic,
        or a JSON response containing the processed data.
    """
    if response_type == "json":
        if not api_key:
            return JSONResponse(
                status_code=403,
                content={"error": "API key required for JSON responses"}
            )
            
        try:
            # Process the query directly for JSON response
            if pattern_type == "include":
                include_patterns = pattern
                exclude_patterns = None
            elif pattern_type == "exclude":
                exclude_patterns = pattern
                include_patterns = None
            else:
                raise ValueError(f"Invalid pattern type: {pattern_type}")

            parsed_query = await parse_query(
                source=input_text,
                max_file_size=log_slider_to_size(max_file_size),
                from_web=True,
                include_patterns=include_patterns,
                ignore_patterns=exclude_patterns,
            )
            
            if not parsed_query.url:
                raise ValueError("The 'url' parameter is required.")

            clone_config = parsed_query.extact_clone_config()
            await clone_repo(clone_config)
            summary, tree, content = ingest_query(parsed_query)
            
            return JSONResponse(content={
                "status": "success",
                "input_text": input_text,
                "max_file_size": max_file_size,
                "pattern_type": pattern_type,
                "pattern": pattern,
                "summary": summary,
                "tree": tree,
                "content": content,
                "ingest_id": parsed_query.id
            })
            
        except Exception as exc:
            error_message = str(exc)
            if "405" in error_message:
                error_message = "Repository not found. Please make sure it is public (private repositories will be supported soon)"
            
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": error_message
                }
            )
    
    # For HTML responses, use the existing process_query function
    return await process_query(
        request,
        input_text,
        max_file_size,
        pattern_type,
        pattern,
        is_index=True,
    )
