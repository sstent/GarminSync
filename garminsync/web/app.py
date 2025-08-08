from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .routes import router

app = FastAPI(title="GarminSync Dashboard")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="garminsync/web/static"), name="static")
templates = Jinja2Templates(directory="garminsync/web/templates")

# Include API routes
app.include_router(router)

@app.get("/")
async def dashboard(request: Request):
    # Get current statistics
    from garminsync.database import get_offline_stats
    stats = get_offline_stats()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": stats
    })
