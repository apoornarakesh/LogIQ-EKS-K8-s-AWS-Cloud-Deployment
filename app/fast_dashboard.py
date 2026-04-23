"""
Fast LogIQ Dashboard - Starts immediately, non-blocking Kafka connection
"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime
import random
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store logs
recent_logs = []
connected_websockets = []
use_sample_logs = True
kafka_available = False

# Sample logs (always available)
def generate_log():
    levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
    sources = ['api', 'database', 'auth', 'payment', 'frontend', 'cache']
    messages = [
        "User login successful",
        "Database query executed in 45ms",
        "Failed to connect to external service",
        "High memory usage detected: 85%",
        "Payment processed for order #12345",
        "Cache hit ratio: 0.78",
        "Rate limit exceeded for API key",
        "Background job completed successfully",
        "New connection established",
        "Request timeout after 30s"
    ]
    return {
        "timestamp": datetime.now().isoformat(),
        "level": random.choice(levels),
        "source": random.choice(sources),
        "message": random.choice(messages)
    }

async def generate_logs_continuously():
    """Generate logs continuously (always works)"""
    count = 0
    while True:
        log = generate_log()
        recent_logs.insert(0, log)
        if len(recent_logs) > 500:
            recent_logs.pop()
        
        # Broadcast to all connected clients
        message = json.dumps(log)
        for ws in connected_websockets[:]:
            try:
                await ws.send_text(message)
            except:
                if ws in connected_websockets:
                    connected_websockets.remove(ws)
        
        await asyncio.sleep(0.2)  # 5 logs per second

async def try_connect_kafka():
    """Try to connect to Kafka in background (non-blocking)"""
    global use_sample_logs, kafka_available
    
    try:
        from kafka import KafkaConsumer
        import threading
        
        def connect_kafka():
            global use_sample_logs, kafka_available
            try:
                consumer = KafkaConsumer(
                    'logiq-logs',
                    bootstrap_servers='localhost:9092',
                    auto_offset_reset='latest',
                    consumer_timeout_ms=5000,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
                )
                kafka_available = True
                use_sample_logs = False
                print("✅ Connected to Kafka! Switching to real logs...")
                
                for msg in consumer:
                    log = msg.value
                    if 'timestamp' not in log:
                        log['timestamp'] = datetime.now().isoformat()
                    recent_logs.insert(0, log)
                    if len(recent_logs) > 500:
                        recent_logs.pop()
                    
                    message = json.dumps(log)
                    for ws in connected_websockets[:]:
                        try:
                            import asyncio
                            asyncio.create_task(ws.send_text(message))
                        except:
                            pass
            except Exception as e:
                print(f"⚠️  Kafka not available: {e}")
                print("📊 Using sample logs...")
        
        # Run Kafka connection in separate thread
        thread = threading.Thread(target=connect_kafka, daemon=True)
        thread.start()
        
    except ImportError:
        print("📊 Kafka module not installed, using sample logs")

@app.on_event("startup")
async def startup_event():
    """Start both log generators"""
    print("\n" + "=" * 50)
    print("🚀 LogIQ Dashboard Started!")
    print("=" * 50)
    print("\n📊 Dashboard URL: http://localhost:8000")
    print("📡 Mode: Sample logs (trying to connect to Kafka in background)")
    print("\n" + "=" * 50 + "\n")
    
    # Start continuous log generation
    asyncio.create_task(generate_logs_continuously())
    
    # Try to connect to Kafka in background
    asyncio.create_task(try_connect_kafka())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    
    # Send recent logs
    for log in recent_logs[-50:]:
        await websocket.send_text(json.dumps(log))
    
    try:
        while True:
            await websocket.receive_text()
    except:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

# Dashboard HTML
HTML = """<!DOCTYPE html>
<html>
<head>
    <title>LogIQ Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 10px;
        }
        .status.sample { background: #f59e0b; color: white; }
        .status.kafka { background: #10b981; color: white; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-number { font-size: 36px; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; margin-top: 10px; }
        .logs-container {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            height: 500px;
            overflow-y: auto;
        }
        .log-entry {
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid;
            font-family: monospace;
            font-size: 12px;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .ERROR { border-left-color: #ef4444; background: #fee; }
        .WARNING { border-left-color: #f59e0b; background: #ffefdb; }
        .INFO { border-left-color: #10b981; background: #d1fae5; }
        .DEBUG { border-left-color: #8b5cf6; background: #ede9fe; }
        .timestamp { color: #999; font-size: 11px; }
        .source { color: #667eea; font-weight: bold; }
        .controls { margin-top: 20px; display: flex; gap: 10px; }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }
        .btn-clear { background: #ef4444; color: white; }
        .filter-btn {
            padding: 5px 15px;
            background: #e5e7eb;
            margin-right: 5px;
            cursor: pointer;
        }
        .filter-btn.active { background: #667eea; color: white; }
        h1 { color: #333; }
        .log-count { font-size: 12px; color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 LogIQ Real-Time Dashboard 
                <span class="status sample" id="status">Sample Mode</span>
            </h1>
            <p>Real-time log streaming - Auto-detects Kafka</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalLogs">0</div>
                <div class="stat-label">Total Logs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="errorCount">0</div>
                <div class="stat-label">Errors</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="logsPerMin">0</div>
                <div class="stat-label">Logs/Minute</div>
            </div>
        </div>
        
        <div style="margin-bottom: 10px;">
            <button class="filter-btn active" onclick="setFilter('ALL')">ALL</button>
            <button class="filter-btn" onclick="setFilter('ERROR')">🔴 ERROR</button>
            <button class="filter-btn" onclick="setFilter('WARNING')">🟡 WARNING</button>
            <button class="filter-btn" onclick="setFilter('INFO')">🔵 INFO</button>
            <button class="filter-btn" onclick="setFilter('DEBUG')">🟣 DEBUG</button>
        </div>
        
        <div class="logs-container" id="logs">
            <div style="text-align: center; color: #999; padding: 20px;">
                Connecting to log stream...
            </div>
        </div>
        
        <div class="controls">
            <button class="btn-clear" onclick="clearLogs()">🗑 Clear All Logs</button>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentFilter = 'ALL';
        let logs = [];
        let logTimes = [];
        
        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws');
            ws.onopen = () => {
                console.log('✅ Connected');
                document.getElementById('status').textContent = 'Connected';
            };
            ws.onmessage = (e) => {
                const log = JSON.parse(e.data);
                addLog(log);
            };
            ws.onclose = () => {
                console.log('❌ Disconnected, reconnecting...');
                setTimeout(connect, 3000);
            };
        }
        
        function addLog(log) {
            logs.unshift(log);
            if(logs.length > 200) logs.pop();
            
            logTimes.push(Date.now());
            logTimes = logTimes.filter(t => Date.now() - t < 60000);
            
            updateDisplay();
        }
        
        function updateDisplay() {
            const filtered = currentFilter === 'ALL' ? logs : logs.filter(l => l.level === currentFilter);
            const container = document.getElementById('logs');
            
            if(filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center;padding:20px;">No logs to display</div>';
                return;
            }
            
            container.innerHTML = filtered.map(log => `
                <div class="log-entry ${log.level}">
                    <span class="timestamp">${new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span class="source">[${log.source}]</span>
                    <span style="font-weight:bold;">${log.level}:</span>
                    ${log.message}
                </div>
            `).join('');
            
            document.getElementById('totalLogs').innerText = logs.length;
            document.getElementById('errorCount').innerText = logs.filter(l => l.level === 'ERROR').length;
            document.getElementById('logsPerMin').innerText = logTimes.length;
        }
        
        function setFilter(level) {
            currentFilter = level;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            updateDisplay();
        }
        
        function clearLogs() {
            logs = [];
            logTimes = [];
            updateDisplay();
        }
        
        connect();
    </script>
</body>
</html>
"""

@app.get("/")
@app.get("/dashboard")
async def root():
    return HTMLResponse(HTML)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
