"""
FastAPI-based REST API for CLIP semantic image search.

Provides production-ready endpoints with:
- Request validation
- Error handling
- CORS support
- Rate limiting ready
- Health checks
- Structured logging
"""

import logging
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from search import (
    CLIPSearchEngine, Config, SearchError,
    InvalidQueryError, InitializationError
)

# Base directory (repo root)
BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "data" / "images"


# ============================================================================
# Setup
# ============================================================================
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ============================================================================
# Pydantic Models
# ============================================================================
class SearchRequest(BaseModel):
    """Request model for image search."""
    
    query: str = Field(
        ...,
        min_length=2,
        max_length=512,
        description="Text query to search for images"
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of results to return"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "query": "a red car on a sunny day",
                "top_k": 5
            }
        }


class SearchResult(BaseModel):
    """Search result item."""
    
    filename: str = Field(..., description="Image filename")
    similarity: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Cosine similarity score"
    )


class SearchResponse(BaseModel):
    """Response model for search requests."""
    
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Number of results returned")
    results: List[SearchResult] = Field(..., description="Search results")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "a red car",
                "total_results": 2,
                "results": [
                    {"filename": "image1.jpg", "similarity": 0.8234},
                    {"filename": "image2.jpg", "similarity": 0.7891}
                ]
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    model: str = Field(..., description="CLIP model name")
    device: str = Field(..., description="Computation device")
    num_images: int = Field(..., description="Number of searchable images")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")


# ============================================================================
# Global Engine
# ============================================================================
search_engine: Optional[CLIPSearchEngine] = None


async def initialize_engine():
    """Initialize CLIP search engine on startup."""
    global search_engine
    try:
        logger.info("Initializing CLIP search engine...")
        search_engine = CLIPSearchEngine()
        logger.info("CLIP search engine initialized successfully")
    except InitializationError as e:
        logger.error(f"Failed to initialize search engine: {str(e)}")
        raise


async def shutdown_engine():
    """Cleanup on shutdown."""
    global search_engine
    if search_engine is not None:
        logger.info("Shutting down CLIP search engine...")
        search_engine.cleanup()


# ============================================================================
# Lifespan Context Manager
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)."""
    # Startup
    await initialize_engine()
    yield
    # Shutdown
    await shutdown_engine()


# ============================================================================
# FastAPI App
# ============================================================================
app = FastAPI(
    title="CLIP Image Search API",
    description="Semantic text-to-image search using CLIP embeddings",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Exception Handlers
# ============================================================================
@app.exception_handler(InvalidQueryError)
async def handle_invalid_query(request, exc: InvalidQueryError):
    """Handle query validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid query",
            "details": str(exc)
        }
    )


@app.exception_handler(SearchError)
async def handle_search_error(request, exc: SearchError):
    """Handle search operation errors."""
    logger.error(f"Search error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Search operation failed",
            "details": str(exc)
        }
    )


@app.exception_handler(Exception)
async def handle_general_error(request, exc: Exception):
    """Handle unexpected errors."""
    logger.exception("Unexpected error")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": "An unexpected error occurred"
        }
    )


# ============================================================================
# Endpoints
# ============================================================================
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and configuration information.
    """
    if search_engine is None:
        raise HTTPException(
            status_code=503,
            detail="Search engine not initialized"
        )
    
    return HealthResponse(
        status="healthy",
        model=search_engine.config.MODEL_NAME,
        device=search_engine.config.DEVICE,
        num_images=search_engine.num_images
    )


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest):
    """
    Search for images by text query.
    
    Performs semantic search using CLIP embeddings to find images
    visually similar to the text description.
    
    Args:
        request: Search request containing query and parameters
        
    Returns:
        SearchResponse with matched images and similarity scores
        
    Raises:
        HTTPException: If search fails or engine not initialized
    """
    if search_engine is None:
        raise HTTPException(
            status_code=503,
            detail="Search engine not initialized"
        )
    
    logger.info(f"Search request: query='{request.query}', top_k={request.top_k}")
    
    try:
        results = search_engine.search(request.query, request.top_k)
        
        return SearchResponse(
            query=request.query,
            total_results=len(results),
            results=[
                SearchResult(filename=filename, similarity=score)
                for filename, score in results
            ]
        )
        
    except InvalidQueryError as e:
        logger.warning(f"Invalid query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except SearchError as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search operation failed")


@app.get("/search", response_model=SearchResponse, tags=["Search"])
async def search_get(
    query: str = Query(..., min_length=2, max_length=512),
    top_k: int = Query(5, ge=1, le=100)
):
    """
    Search for images by text query (GET endpoint).
    
    Query parameters:
        query: Text query to search for images
        top_k: Number of results to return (default: 5, max: 100)
    """
    request = SearchRequest(query=query, top_k=top_k)
    return await search(request)


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "CLIP Image Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "POST /search": "Search with JSON body",
            "GET /search": "Search with query parameters",
            "GET /health": "Health check",
            "GET /images/{filename}": "Download search result image"
        }
    }


@app.get("/images/{filename}", tags=["Images"])
async def get_image(filename: str):
    """
    Serve image file from search results.
    
    Args:
        filename: Image filename (e.g., 'IMG_6fae0c05.jpg')
        
    Returns:
        Image file with appropriate content-type
        
    Raises:
        HTTPException 404: If image not found
    """
    # Security: prevent path traversal
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    image_path = IMAGES_DIR / filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {filename}")
    
    return FileResponse(
        image_path,
        media_type="image/jpeg" if filename.endswith((".jpg", ".jpeg")) else "image/png"
    )


# ============================================================================
# Development Server
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    # Run with: uvicorn api:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
