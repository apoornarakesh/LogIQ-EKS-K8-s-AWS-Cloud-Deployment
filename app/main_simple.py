"""
Simplified LogIQ Dashboard - No database dependencies
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
import json
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Any

app = FastAPI(title="LogIQ Dashboard", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample log generator
log_sources = ['api', 'database', 'auth', 'payment', 'frontend', 'cache', 'worker']
log_levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG', 'CRITICAL']
log_messages = {
    'api': [
        "GET /api/users took {duration}ms",
        "POST /api/login from IP {ip}",
        "Rate limit exceeded for API key",
        "Request timeout after {timeout}s"
    ],
    'database': [
        "Query executed in {duration}ms",
        "Connection pool exhausted",
        "Deadlock detected on table {table}",
        "Slow query: {query} took {duration}s"
    ],
    'auth': [
        "User {user} logged in successfully",
        "Failed login attempt for {user} from {ip}",
        "Session expired for user {user}",
        "Invalid token provided"
    ],
    'payment': [
        "Payment of ${amount} processed for order {order}",
        "Payment failed: insufficient funds",
        "Refund issued for order {order}",
        "Payment gateway timeout"
    ],
    'frontend': [
        "Page load time: {duration}ms",
        "API call to {endpoint} failed",
        "User clicked on {element}"
    ],
    'cache': [
        "Cache hit for key {key}",
        "Cache miss for key {key}",
        "Cache evicted {count} items"
    ],
    'worker': [
        "Processing job {job_id}",
        "Job {job_id} completed in {duration}s",
        "Job {job_id} failed, retrying"
    ]
}

def generate_log() -> Dict[str, Any]:
    """Generate a random log entry"""
    source = random.choice(log_sources)
    
    # Weighted distribution for more realistic logs
    rand = random.random()
    if rand < 0.7:
        level = 'INFO'
    elif rand < 0.85:
        level = 'WARNING'
    elif rand < 0.95:
        level = 'ERROR'
    else:
        level = 'CRITICAL'
    
    # Get message template
    messages = log_messages.get(source, ["Processed request"])
    template = random.choice(messages)
    
    # Fill in placeholders
    message = template.format(
        duration=random.randint(10, 500),
        ip=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        timeout=random.randint(5, 60),
        table=random.choice(['users', 'orders', 'products', 'logs']),
        query=random.choice(['SELECT', 'INSERT', 'UPDATE', 'DELETE']),
        user=f"user_{random.randint(1, 1000)}",
        amount=random.randint(10, 1000),
        order=f"ORD-{random.randint(10000, 99999)}",
        endpoint=random.choice(['/api/users', '/api/orders', '/api/login']),
        element=random.choice(['button', 'link', 'form', 'dropdown']),
        key=random.choice(['user:123', 'session:abc', 'product:456']),
        count=random.randint(1, 100),
        job_id=f"job_{random.randint(1000, 9999)}"
    )
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "source": source,
        "message": message,
        "metadata": {
            "trace_id": f"trace_{random.randint(1000, 9999)}",
            "host": f"server-{random.randint(1, 5)}"
        }
    }

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

async def log_generator(websocket: WebSocket, rate: int = 20):
    """Generate logs at specified rate (logs per second)"""
    delay = 1.0 / rate
    running = True
    
    while running:
        try:
            log = generate_log()
            await websocket.send_text(json.dumps(log))
            await asyncio.sleep(delay)
        except:
            running = False
            break

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time logs"""
    await manager.connect(websocket)
    
    generator_task = None
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                
                if msg.get('action') == 'start':
                    if generator_task:
                        generator_task.cancel()
                    generator_task = asyncio.create_task(log_generator(websocket, rate=20))
                    await websocket.send_text(json.dumps({"status": "started"}))
                elif msg.get('action') == 'stop':
                    if generator_task:
                        generator_task.cancel()
                        generator_task = None
                        await websocket.send_text(json.dumps({"status": "stopped"}))
            except json.JSONDecodeError:
                pass
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if generator_task:
            generator_task.cancel()
        manager.disconnect(websocket)

# Dashboard HTML
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogIQ - Real-Time Log Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .dashboard { max-width: 1600px; margin: 0 auto; }
        .header {
            background: white;
            border-radius: 15px;
            padding: 20px 30px;
            margin-bottom: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
            display: inline-block;
        }
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-icon { font-size: 32px; margin-bottom: 10px; }
        .stat-value { font-size: 36px; font-weight: bold; color: #333; }
        .stat-label { color: #666; font-size: 14px; margin-top: 5px; }
        .logs-section {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .filter-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .filter-btn.active {
            background: #667eea;
            color: white;
        }
        .filter-btn:not(.active) {
            background: #e5e7eb;
            color: #666;
        }
        .logs-table {
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #f9fafb;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 13px;
        }
        .severity-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }
        .severity-ERROR { background: #fee2e2; color: #dc2626; }
        .severity-CRITICAL { background: #fecaca; color: #991b1b; }
        .severity-WARNING { background: #fed7aa; color: #ea580c; }
        .severity-INFO { background: #d1fae5; color: #059669; }
        .severity-DEBUG { background: #e0e7ff; color: #4f46e5; }
        .log-message {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-width: 500px;
            word-break: break-word;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-secondary { background: #6b7280; color: white; }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>📊 LogIQ Real-Time Dashboard</h1>
            <div><span class="status-dot"></span> <span style="margin-left: 8px;">Live Streaming</span></div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📝</div>
                <div class="stat-value" id="totalLogs">0</div>
                <div class="stat-label">Total Logs</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">❌</div>
                <div class="stat-value" id="errorCount">0</div>
                <div class="stat-label">Errors</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⚠️</div>
                <div class="stat-value" id="warnCount">0</div>
                <div class="stat-label">Warnings</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">⚡</div>
                <div class="stat-value" id="logsRate">0</div>
                <div class="stat-label">Logs/Minute</div>
            </div>
        </div>
        
        <div class="logs-section">
            <div class="section-header">
                <h3>Recent Logs</h3>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="setFilter('ALL')">All</button>
                    <button class="filter-btn" onclick="setFilter('ERROR')">🔴 Errors</button>
                    <button class="filter-btn" onclick="setFilter('WARNING')">🟡 Warnings</button>
                    <button class="filter-btn" onclick="setFilter('INFO')">🔵 Info</button>
                </div>
            </div>
            <div class="logs-table">
                <table>
                    <thead>
                        <tr><th>Time</th><th>Severity</th><th>Source</th><th>Message</th></tr>
                    </thead>
                    <tbody id="logsBody"><tr><td colspan="4" style="text-align:center;">Connecting...</td></tr></tbody>
                </table>
            </div>
            <div class="controls">
                <button class="btn btn-danger" onclick="stopStreaming()">⏹ Stop</button>
                <button class="btn btn-primary" onclick="startStreaming()">▶ Start</button>
                <button class="btn btn-secondary" onclick="clearLogs()">🗑 Clear</button>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentFilter = 'ALL';
        let logs = [];
        let streaming = true;
        
        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws/logs');
            ws.onopen = () => { console.log('Connected'); startStreaming(); };
            ws.onmessage = (e) => { if(streaming) addLog(JSON.parse(e.data)); };
            ws.onclose = () => setTimeout(connect, 3000);
        }
        
        function addLog(log) {
            logs.unshift(log);
            if(logs.length > 100) logs.pop();
            updateUI();
        }
        
        function updateUI() {
            const filtered = currentFilter === 'ALL' ? logs : logs.filter(l => l.level === currentFilter);
            const tbody = document.getElementById('logsBody');
            
            if(filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No logs</td></tr>';
            } else {
                tbody.innerHTML = filtered.slice(0, 50).map(log => `
                    <tr>
                        <td style="white-space:nowrap;">${new Date(log.timestamp).toLocaleTimeString()}</td>
                        <td><span class="severity-badge severity-${log.level}">${log.level}</span></td>
                        <td>${log.source}</td>
                        <td class="log-message" title="${log.message}">${log.message.substring(0, 80)}</td>
                    </tr>
                `).join('');
            }
            
            document.getElementById('totalLogs').innerText = logs.length;
            const errors = logs.filter(l => l.level === 'ERROR' || l.level === 'CRITICAL').length;
            const warns = logs.filter(l => l.level === 'WARNING').length;
            document.getElementById('errorCount').innerText = errors;
            document.getElementById('warnCount').innerText = warns;
            
            const now = Date.now();
            const recent = logs.filter(l => (now - new Date(l.timestamp).getTime()) < 60000).length;
            document.getElementById('logsRate').innerText = recent;
        }
        
        function setFilter(level) {
            currentFilter = level;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            updateUI();
        }
        
        function startStreaming() { streaming = true; if(ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({action: 'start'})); }
        function stopStreaming() { streaming = false; if(ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({action: 'stop'})); }
        function clearLogs() { logs = []; updateUI(); }
        
        connect();
    </script>
</body>
</html>'''

@app.get("/")
@app.get("/dashboard")
async def dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "LogIQ"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
