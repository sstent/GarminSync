from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from .routes import router

app = FastAPI(title="GarminSync Dashboard")

# Get the current directory path
current_dir = Path(__file__).parent

# Mount static files and templates with error handling
static_dir = current_dir / "static"
templates_dir = current_dir / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))
else:
    templates = None

# Include API routes
app.include_router(router)

@app.get("/")
async def dashboard(request: Request):
    """Dashboard route with fallback for missing templates"""
    if not templates:
        # Return JSON response if templates are not available
        from garminsync.database import get_offline_stats
        stats = get_offline_stats()
        return JSONResponse({
            "message": "GarminSync Dashboard",
            "stats": stats,
            "note": "Web UI templates not found, showing JSON response"
        })
    
    try:
        # Get current statistics
        from garminsync.database import get_offline_stats
        stats = get_offline_stats()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "stats": stats
        })
    except Exception as e:
        return JSONResponse({
            "error": f"Failed to load dashboard: {str(e)}",
            "message": "Dashboard unavailable, API endpoints still functional"
        })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "GarminSync Dashboard"}

@app.get("/config")
async def config_page(request: Request):
    """Configuration page"""
    if not templates:
        return JSONResponse({
            "message": "Configuration endpoint",
            "note": "Use /api/schedule endpoints for configuration"
        })
    
    return templates.TemplateResponse("config.html", {
        "request": request
    })

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )