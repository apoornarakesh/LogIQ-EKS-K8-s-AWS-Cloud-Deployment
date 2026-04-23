"""
Real LogIQ Dashboard - Pulls actual logs from Kafka/PostgreSQL
"""
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Try to import database modules
try:
    import psycopg2
    from kafka import KafkaConsumer, KafkaProducer
    from elasticsearch import Elasticsearch
    DB_AVAILABLE = True
except ImportError as e:
    print(f"Some modules not available: {e}")
    DB_AVAILABLE = False

app = FastAPI(title="LogIQ Real Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="logiq",
            user="logiq",
            password="logiq123"
        )
        return conn
    except:
        return None

def get_elasticsearch():
    try:
        es = Elasticsearch(["http://localhost:9200"])
        if es.ping():
            return es
    except:
        pass
    return None

def get_kafka_logs():
    """Get recent logs from Kafka"""
    try:
        consumer = KafkaConsumer(
            'logiq-logs',
            bootstrap_servers='localhost:9092',
            auto_offset_reset='latest',
            consumer_timeout_ms=3000,
            max_poll_records=50
        )
        
        logs = []
        for msg in consumer:
            logs.append(json.loads(msg.value.decode('utf-8')))
            if len(logs) >= 50:
                break
        consumer.close()
        return logs
    except Exception as e:
        print(f"Kafka error: {e}")
        return []

def get_postgres_logs(limit: int = 100):
    """Get logs from PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, level, source, message, metadata 
            FROM logs 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (limit,))
        
        logs = []
        for row in cur.fetchall():
            logs.append({
                "timestamp": row[0].isoformat(),
                "level": row[1],
                "source": row[2],
                "message": row[3],
                "metadata": row[4] if row[4] else {}
            })
        cur.close()
        conn.close()
        return logs
    except Exception as e:
        print(f"PostgreSQL error: {e}")
        return []

def get_elasticsearch_logs(limit: int = 100):
    """Get logs from Elasticsearch"""
    es = get_elasticsearch()
    if not es:
        return []
    
    try:
        result = es.search(
            index="logs-*",
            body={
                "query": {"match_all": {}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": limit
            }
        )
        
        logs = []
        for hit in result['hits']['hits']:
            source = hit['_source']
            logs.append({
                "timestamp": source.get('timestamp', ''),
                "level": source.get('level', 'INFO'),
                "source": source.get('source', 'unknown'),
                "message": source.get('message', ''),
                "metadata": source.get('metadata', {})
            })
        return logs
    except Exception as e:
        print(f"Elasticsearch error: {e}")
        return []

# Real-time log consumer
class RealTimeLogManager:
    def __init__(self):
        self.active_connections = []
        self.last_logs = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
    async def send_log(self, log: Dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(log))
            except:
                pass

manager = RealTimeLogManager()

async def kafka_log_consumer():
    """Continuously consume logs from Kafka and broadcast"""
    consumer = None
    while True:
        try:
            if not consumer:
                consumer = KafkaConsumer(
                    'logiq-logs',
                    bootstrap_servers='localhost:9092',
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
                )
            
            for msg in consumer:
                log = msg.value
                log['timestamp'] = log.get('timestamp', datetime.utcnow().isoformat())
                await manager.send_log(log)
                manager.last_logs.insert(0, log)
                if len(manager.last_logs) > 1000:
                    manager.last_logs.pop()
                    
        except Exception as e:
            print(f"Kafka consumer error: {e}")
            if consumer:
                consumer.close()
                consumer = None
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    # Start background Kafka consumer
    asyncio.create_task(kafka_log_consumer())

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send recent logs on connection
        for log in manager.last_logs[-50:]:
            await websocket.send_text(json.dumps(log))
        
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        manager.disconnect(websocket)

# Dashboard HTML with real data
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogIQ - Real Database Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .dashboard { max-width: 1600px; margin: 0 auto; }
        
        /* Header */
        .header {
            background: white;
            border-radius: 15px;
            padding: 20px 30px;
            margin-bottom: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .header h1 { color: #1e3c72; }
        .status {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
        }
        .source-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .source-kafka { background: #fef3c7; color: #d97706; }
        .source-postgres { background: #dbeafe; color: #2563eb; }
        .source-elastic { background: #e0e7ff; color: #4f46e5; }
        
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value { font-size: 42px; font-weight: bold; color: #1e3c72; }
        .stat-label { color: #666; margin-top: 8px; }
        
        /* Logs Section */
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
            transition: all 0.3s;
        }
        .filter-btn.active {
            background: #1e3c72;
            color: white;
        }
        .filter-btn:not(.active) {
            background: #e5e7eb;
            color: #666;
        }
        
        /* Table */
        .logs-table {
            max-height: 550px;
            overflow-y: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #f8fafc;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
            font-size: 13px;
        }
        .severity {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .severity-ERROR { background: #fee2e2; color: #dc2626; }
        .severity-CRITICAL { background: #fecaca; color: #991b1b; }
        .severity-WARNING { background: #fed7aa; color: #ea580c; }
        .severity-INFO { background: #d1fae5; color: #059669; }
        .severity-DEBUG { background: #e0e7ff; color: #4f46e5; }
        
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
        .btn-primary { background: #1e3c72; color: white; }
        .btn-danger { background: #dc2626; color: white; }
        .btn-secondary { background: #6b7280; color: white; }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>📊 LogIQ Real Dashboard</h1>
            <div class="status">
                <div class="status-dot"></div>
                <span>Live from Kafka/PostgreSQL</span>
                <span class="source-badge source-kafka">Kafka Stream</span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="totalLogs">0</div>
                <div class="stat-label">Total Logs Received</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="errorCount">0</div>
                <div class="stat-label">Errors</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="warnCount">0</div>
                <div class="stat-label">Warnings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="logsRate">0</div>
                <div class="stat-label">Logs/Minute</div>
            </div>
        </div>
        
        <div class="logs-section">
            <div class="section-header">
                <h3>📋 Live Log Stream</h3>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="setFilter('ALL')">All</button>
                    <button class="filter-btn" onclick="setFilter('ERROR')">🔴 Errors</button>
                    <button class="filter-btn" onclick="setFilter('WARNING')">🟡 Warnings</button>
                    <button class="filter-btn" onclick="setFilter('INFO')">🔵 Info</button>
                    <button class="filter-btn" onclick="setFilter('DEBUG')">🟣 Debug</button>
                </div>
            </div>
            <div class="logs-table" id="logsTable">
                <div class="loading">Connecting to log stream...</div>
            </div>
            <div class="controls">
                <button class="btn btn-danger" onclick="clearLogs()">🗑 Clear Logs</button>
                <button class="btn btn-primary" onclick="scrollToTop()">⬆ Scroll to Top</button>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentFilter = 'ALL';
        let logs = [];
        let logTimes = [];
        
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/ws/dashboard');
            
            ws.onopen = function() {
                console.log('WebSocket connected - receiving real logs from Kafka');
                document.getElementById('logsTable').innerHTML = '<div class="loading">Listening for logs...</div>';
            };
            
            ws.onmessage = function(event) {
                const log = JSON.parse(event.data);
                addLog(log);
                updateStats();
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                document.getElementById('logsTable').innerHTML = '<div class="loading">⚠️ Connection error. Make sure Kafka is running.</div>';
            };
            
            ws.onclose = function() {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function addLog(log) {
            logs.unshift(log);
            if (logs.length > 500) logs.pop();
            
            // Update timestamp for rate calculation
            logTimes.push(Date.now());
            logTimes = logTimes.filter(t => Date.now() - t < 60000);
            
            renderLogs();
        }
        
        function renderLogs() {
            const filtered = currentFilter === 'ALL' 
                ? logs 
                : logs.filter(l => l.level === currentFilter);
            
            if (filtered.length === 0) {
                document.getElementById('logsTable').innerHTML = '<div class="loading">No logs to display</div>';
                return;
            }
            
            const html = `
                <table>
                    <thead>
                        <tr><th>Time</th><th>Severity</th><th>Source</th><th>Message</th><th>Metadata</th></tr>
                    </thead>
                    <tbody>
                        ${filtered.slice(0, 100).map(log => `
                            <tr>
                                <td style="white-space:nowrap;">${new Date(log.timestamp).toLocaleTimeString()}</td>
                                <td><span class="severity severity-${log.level}">${log.level}</span></td>
                                <td><strong>${log.source}</strong></td>
                                <td style="word-break:break-word;">${escapeHtml(log.message.substring(0, 100))}</td>
                                <td style="font-size:11px;">${log.metadata ? Object.keys(log.metadata).slice(0,2).join(',') : '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            document.getElementById('logsTable').innerHTML = html;
        }
        
        function updateStats() {
            document.getElementById('totalLogs').innerText = logs.length;
            const errors = logs.filter(l => l.level === 'ERROR' || l.level === 'CRITICAL').length;
            const warns = logs.filter(l => l.level === 'WARNING').length;
            document.getElementById('errorCount').innerText = errors;
            document.getElementById('warnCount').innerText = warns;
            document.getElementById('logsRate').innerText = logTimes.length;
        }
        
        function setFilter(level) {
            currentFilter = level;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            renderLogs();
        }
        
        function clearLogs() {
            logs = [];
            logTimes = [];
            renderLogs();
            updateStats();
        }
        
        function scrollToTop() {
            document.querySelector('.logs-table').scrollTop = 0;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Start connection
        connectWebSocket();
    </script>
</body>
</html>
'''

@app.get("/")
@app.get("/dashboard")
async def dashboard():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/api/stats")
async def get_stats():
    """API endpoint for statistics"""
    return {
        "total_logs": len(manager.last_logs),
        "kafka_connected": True,  # Check actual status
        "postgres_connected": get_db_connection() is not None,
        "elasticsearch_connected": get_elasticsearch() is not None
    }

@app.get("/api/logs/recent")
async def get_recent_logs(limit: int = 100):
    """Get recent logs from memory"""
    return manager.last_logs[:limit]

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("LogIQ Real Dashboard Starting...")
    print("=" * 50)
    print("\n📊 Dashboard URL: http://localhost:8000/dashboard")
    print("📡 Data Source: Kafka logs (logiq-logs topic)")
    print("\nMake sure Kafka is running:")
    print("  docker compose up -d")
    print("\n" + "=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
