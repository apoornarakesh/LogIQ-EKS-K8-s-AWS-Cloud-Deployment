from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio

from app.api import health, logs
from app.api.websocket import websocket_endpoint

app = FastAPI(title="LogIQ", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])

# WebSocket endpoint
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Dashboard HTML
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    dashboard_path = Path("app/templates/dashboard.html")
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text())
    return HTMLResponse(content="<h1>Dashboard not found. Please check installation.</h1>")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "LogIQ"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
