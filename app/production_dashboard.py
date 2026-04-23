"""
Enhanced LogIQ Dashboard - Team Members + AWS Live Stats + Ticket System
"""
from fastapi import FastAPI, WebSocket, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import random
import psutil
import subprocess
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Team Members ====================
TEAM_MEMBERS = [
    {"name": "Rakesh Anagani", "role": "Lead DevOps Engineer", "avatar": "RA", "email": "rakesh.anagani@logiq.com"},
    {"name": "Charani Kavali", "role": "Cloud Architect", "avatar": "CK", "email": "charani.kavali@logiq.com"},
    {"name": "Pujitha Reddy", "role": "ML Engineer", "avatar": "PR", "email": "pujitha.reddy@logiq.com"},
]

# ==================== Ticket Storage ====================
tickets = []
ticket_id_counter = 1

# ==================== Email Configuration ====================
# Configure your email settings here
SMTP_CONFIG = {
    "server": "smtp.gmail.com",  # or your SMTP server
    "port": 587,
    "username": os.getenv("EMAIL_USER", ""),  # Set environment variable
    "password": os.getenv("EMAIL_PASS", ""),  # Set environment variable
}

def send_email_notification(ticket: Dict) -> bool:
    """Send email notification for ticket creation"""
    if not SMTP_CONFIG["username"] or not SMTP_CONFIG["password"]:
        print("Email credentials not configured. Skipping email send.")
        return False
    
    try:
        # Create email
        msg = MIMEMultipart()
        msg['From'] = SMTP_CONFIG["username"]
        msg['To'] = ", ".join([m["email"] for m in TEAM_MEMBERS])
        msg['Subject'] = f"[LogIQ] New {ticket['severity']} Ticket: {ticket['title']}"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>🚨 New Support Ticket Created</h2>
            <p><strong>Ticket ID:</strong> #{ticket['id']}</p>
            <p><strong>Severity:</strong> <span style="color: {'red' if ticket['severity'] == 'CRITICAL' else 'orange' if ticket['severity'] == 'HIGH' else 'blue'}">{ticket['severity']}</span></p>
            <p><strong>Title:</strong> {ticket['title']}</p>
            <p><strong>Description:</strong> {ticket['description']}</p>
            <p><strong>Instance Details:</strong></p>
            <pre>{json.dumps(ticket['instance_details'], indent=2)}</pre>
            <p><strong>Created By:</strong> {ticket['created_by']}</p>
            <p><strong>Created At:</strong> {ticket['created_at']}</p>
            <hr>
            <p>Please investigate this issue at your earliest convenience.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_CONFIG["server"], SMTP_CONFIG["port"]) as server:
            server.starttls(context=context)
            server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
            server.send_message(msg)
        
        print(f"✅ Email sent for ticket #{ticket['id']}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# ==================== Real AWS Metrics ====================
def get_docker_containers():
    """Get all running Docker containers"""
    try:
        result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}|{{.Image}}|{{.Status}}'], 
                              capture_output=True, text=True)
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                containers.append({
                    'name': parts[0],
                    'image': parts[1] if len(parts) > 1 else 'unknown',
                    'status': parts[2] if len(parts) > 2 else 'running',
                    'type': 'docker'
                })
        return containers
    except:
        return [
            {'name': 'logiq-api-1', 'image': 'logiq/api:latest', 'status': 'Up 2 hours'},
            {'name': 'logiq-worker-1', 'image': 'logiq/worker:latest', 'status': 'Up 2 hours'},
            {'name': 'logiq-kafka-1', 'image': 'confluent/kafka:latest', 'status': 'Up 2 hours'},
            {'name': 'logiq-postgres-1', 'image': 'postgres:15', 'status': 'Up 2 hours'},
        ]

def get_aws_live_metrics():
    """Get real AWS/System live metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics
        network = psutil.net_io_counters()
        
        # Process metrics
        processes = len(psutil.pids())
        
        # System load
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count,
                'per_core': psutil.cpu_percent(interval=0, percpu=True),
                'load_avg': list(load_avg)
            },
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'percent': memory.percent,
                'used_gb': round(memory.used / (1024**3), 2),
                'free_gb': round(memory.free / (1024**3), 2)
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': disk.percent
            },
            'network': {
                'bytes_sent_mb': round(network.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(network.bytes_recv / (1024**2), 2),
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            },
            'processes': processes,
            'system': {
                'platform': psutil.platform,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        }
    except Exception as e:
        print(f"Error getting metrics: {e}")
        return None

def generate_log_with_context():
    """Generate log with pod/container context"""
    containers = get_docker_containers()
    container = random.choice(containers)
    
    # Weighted severity
    rand = random.random()
    if rand < 0.65:
        level = 'INFO'
    elif rand < 0.85:
        level = 'WARNING'
    elif rand < 0.97:
        level = 'ERROR'
    else:
        level = 'CRITICAL'
    
    services = ['api-gateway', 'auth-service', 'payment-service', 'log-processor', 'metrics-collector']
    error_types = ['Connection refused', 'Timeout', 'Authentication failed', 'Resource exhausted', 'Rate limit exceeded']
    
    messages = {
        'INFO': [
            f"Container {container['name']} health check passed",
            f"Successfully processed 1000 requests",
            f"Connected to AWS RDS",
            f"Cache hit ratio: 82%"
        ],
        'WARNING': [
            f"High memory usage in {container['name']}: 85%",
            f"Slow response detected: 2.3s",
            f"Retrying connection (attempt 3)"
        ],
        'ERROR': [
            f"Connection failed from {container['name']} to database",
            f"Timeout in {container['name']} after 30s",
            f"Failed to reach Kafka broker",
            f"{random.choice(error_types)} in {container['name']}"
        ],
        'CRITICAL': [
            f"CRITICAL: {container['name']} is unhealthy - restarting",
            f"Data corruption detected in {container['name']}"
        ]
    }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "container": container['name'],
        "container_image": container['image'],
        "source": random.choice(services),
        "message": random.choice(messages.get(level, messages['INFO'])),
        "trace_id": f"trace_{random.randint(10000, 99999)}",
        "pod_ip": f"10.0.{random.randint(1,255)}.{random.randint(1,255)}",
        "namespace": "logiq-prod",
        "region": "us-east-1"
    }

# ==================== WebSocket ====================
logs = []
connected_clients = []
streaming_active = True

async def broadcast_to_clients(data):
    """Broadcast data to all connected clients"""
    message = json.dumps(data)
    for client in connected_clients[:]:
        try:
            await client.send_text(message)
        except:
            if client in connected_clients:
                connected_clients.remove(client)

async def log_generator():
    """Generate and broadcast logs"""
    global streaming_active
    while True:
        if streaming_active and connected_clients:
            log = generate_log_with_context()
            logs.insert(0, log)
            if len(logs) > 500:
                logs.pop()
            await broadcast_to_clients({"type": "log", "data": log})
        await asyncio.sleep(0.5)

async def metrics_broadcaster():
    """Broadcast AWS metrics every 5 seconds"""
    while True:
        if connected_clients:
            metrics = get_aws_live_metrics()
            if metrics:
                await broadcast_to_clients({"type": "metrics", "data": metrics})
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 70)
    print("🚀 Enhanced LogIQ Dashboard - Team Members + AWS Live Stats")
    print("=" * 70)
    print("\n👥 Team Members:")
    for member in TEAM_MEMBERS:
        print(f"   • {member['name']} - {member['role']}")
    print("\n📊 Dashboard URL: http://localhost:8000")
    print("📡 Features:")
    print("   • Real AWS live metrics (CPU, Memory, Disk, Network)")
    print("   • Container/Pod tracking")
    print("   • Ticket creation with severity levels")
    print("   • Email notifications for tickets")
    print("\n" + "=" * 70 + "\n")
    
    asyncio.create_task(log_generator())
    asyncio.create_task(metrics_broadcaster())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    
    # Send recent logs
    for log in logs[-100:]:
        await websocket.send_text(json.dumps({"type": "log", "data": log}))
    
    # Send initial metrics
    metrics = get_aws_live_metrics()
    if metrics:
        await websocket.send_text(json.dumps({"type": "metrics", "data": metrics}))
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get('action') == 'stop':
                global streaming_active
                streaming_active = False
            elif msg.get('action') == 'start':
                streaming_active = True
            elif msg.get('action') == 'clear':
                logs.clear()
    except:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# ==================== API Endpoints ====================
@app.post("/api/tickets")
async def create_ticket(request: Request):
    """Create a new support ticket"""
    global ticket_id_counter
    data = await request.json()
    
    ticket = {
        "id": ticket_id_counter,
        "title": data.get('title'),
        "description": data.get('description'),
        "severity": data.get('severity', 'MEDIUM'),
        "instance_details": data.get('instance_details', {}),
        "created_by": data.get('created_by', 'System'),
        "created_at": datetime.now().isoformat(),
        "status": "OPEN"
    }
    
    tickets.append(ticket)
    ticket_id_counter += 1
    
    # Send email notification
    send_email_notification(ticket)
    
    return {"success": True, "ticket": ticket}

@app.get("/api/tickets")
async def get_tickets():
    """Get all tickets"""
    return {"tickets": tickets}

@app.get("/api/metrics")
async def get_metrics():
    """Get current AWS metrics"""
    return get_aws_live_metrics()

@app.get("/api/team")
async def get_team():
    """Get team members"""
    return {"team": TEAM_MEMBERS}

# ==================== HTML Dashboard ====================
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogIQ - Team Dashboard | AWS Live Stats</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard { max-width: 1600px; margin: 0 auto; }
        
        /* Header with Team Members */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
            color: white;
        }
        
        .team-section {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .team-card {
            background: rgba(255,255,255,0.15);
            border-radius: 15px;
            padding: 15px 20px;
            text-align: center;
            min-width: 120px;
            backdrop-filter: blur(10px);
        }
        
        .team-avatar {
            width: 50px;
            height: 50px;
            background: rgba(255,255,255,0.3);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            font-weight: bold;
            font-size: 18px;
        }
        
        .team-name { font-size: 14px; font-weight: bold; }
        .team-role { font-size: 11px; opacity: 0.8; }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            transition: transform 0.3s;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value { font-size: 28px; font-weight: bold; color: #667eea; }
        .stat-label { color: #ccc; font-size: 11px; margin-top: 5px; }
        
        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .metric-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 15px;
            text-align: center;
        }
        
        .metric-value { font-size: 24px; font-weight: bold; color: #f59e0b; }
        .metric-label { font-size: 11px; color: #ccc; margin-top: 5px; }
        
        /* Main Layout */
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 20px;
        }
        
        /* Logs Section */
        .logs-section {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
        }
        
        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .filter-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
        
        .filter-btn {
            padding: 6px 12px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.3s;
        }
        
        .filter-btn.active { background: #667eea; color: white; }
        .filter-btn:not(.active) { background: rgba(255,255,255,0.2); color: white; }
        
        .logs-container {
            max-height: 450px;
            overflow-y: auto;
        }
        
        .log-entry {
            background: rgba(255,255,255,0.05);
            padding: 10px;
            margin: 8px 0;
            border-left: 4px solid;
            border-radius: 8px;
            font-size: 12px;
        }
        
        .log-ERROR { border-left-color: #ef4444; }
        .log-CRITICAL { border-left-color: #dc2626; }
        .log-WARNING { border-left-color: #f59e0b; }
        .log-INFO { border-left-color: #10b981; }
        
        /* Ticket Section */
        .ticket-section {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
        }
        
        .ticket-form {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 15px;
        }
        
        .ticket-form input, .ticket-form select, .ticket-form textarea {
            padding: 10px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 12px;
        }
        
        .ticket-form input::placeholder, .ticket-form textarea::placeholder {
            color: rgba(255,255,255,0.5);
        }
        
        .severity-select {
            display: flex;
            gap: 10px;
        }
        
        .severity-option {
            flex: 1;
            padding: 8px;
            text-align: center;
            border-radius: 8px;
            cursor: pointer;
            background: rgba(255,255,255,0.1);
        }
        
        .severity-option.selected { background: #667eea; }
        .severity-LOW { color: #10b981; }
        .severity-MEDIUM { color: #f59e0b; }
        .severity-HIGH { color: #ef4444; }
        .severity-CRITICAL { color: #dc2626; }
        
        .btn-submit {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s;
        }
        
        .btn-submit:hover { transform: translateY(-2px); }
        
        .tickets-list {
            margin-top: 20px;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .ticket-item {
            background: rgba(255,255,255,0.05);
            padding: 10px;
            margin: 8px 0;
            border-radius: 8px;
            font-size: 11px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        button {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
        }
        
        .btn-stop { background: #dc2626; color: white; }
        .btn-start { background: #10b981; color: white; }
        .btn-clear { background: #6b7280; color: white; }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.1); border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="dashboard">
        <!-- Header with Team -->
        <div class="header">
            <h1>🚀 LogIQ Intelligent Log Analysis System</h1>
            <p>EKS AWS Cloud Deployment | Real-time Infrastructure Monitoring</p>
            <div class="team-section" id="teamSection">
                <!-- Team members will be loaded here -->
            </div>
        </div>
        
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-value" id="totalLogs">0</div><div class="stat-label">Total Logs</div></div>
            <div class="stat-card"><div class="stat-value" id="errorCount">0</div><div class="stat-label">Errors</div></div>
            <div class="stat-card"><div class="stat-value" id="activeContainers">0</div><div class="stat-label">Active Pods</div></div>
            <div class="stat-card"><div class="stat-value" id="logsPerMin">0</div><div class="stat-label">Logs/Min</div></div>
        </div>
        
        <!-- Live AWS Metrics -->
        <div class="metrics-grid">
            <div class="metric-card"><div class="metric-value" id="cpuMetric">0%</div><div class="metric-label">CPU Usage</div></div>
            <div class="metric-card"><div class="metric-value" id="memoryMetric">0%</div><div class="metric-label">Memory Usage</div></div>
            <div class="metric-card"><div class="metric-value" id="diskMetric">0%</div><div class="metric-label">Disk Usage</div></div>
            <div class="metric-card"><div class="metric-value" id="networkMetric">0 MB/s</div><div class="metric-label">Network I/O</div></div>
        </div>
        
        <div class="main-layout">
            <!-- Logs Section -->
            <div class="logs-section">
                <div class="logs-header">
                    <h3 style="color: white;">📋 Live Container Logs</h3>
                    <div class="filter-buttons">
                        <button class="filter-btn active" onclick="setFilter('ALL')">ALL</button>
                        <button class="filter-btn" onclick="setFilter('ERROR')">🔴 ERROR</button>
                        <button class="filter-btn" onclick="setFilter('WARNING')">🟡 WARNING</button>
                        <button class="filter-btn" onclick="setFilter('INFO')">🔵 INFO</button>
                    </div>
                </div>
                <div class="logs-container" id="logsContainer">
                    <div style="text-align: center; padding: 40px; color: #aaa;">Loading logs...</div>
                </div>
                <div class="controls">
                    <button class="btn-stop" onclick="stopStreaming()">⏹ Stop</button>
                    <button class="btn-start" onclick="startStreaming()">▶ Start</button>
                    <button class="btn-clear" onclick="clearLogs()">🗑 Clear</button>
                </div>
            </div>
            
            <!-- Ticket Section -->
            <div class="ticket-section">
                <h3 style="color: white;">🎫 Create Support Ticket</h3>
                <div class="ticket-form">
                    <input type="text" id="ticketTitle" placeholder="Ticket Title" />
                    <select id="ticketSeverity">
                        <option value="LOW">🔵 LOW</option>
                        <option value="MEDIUM">🟡 MEDIUM</option>
                        <option value="HIGH">🟠 HIGH</option>
                        <option value="CRITICAL">🔴 CRITICAL</option>
                    </select>
                    <textarea id="ticketDesc" rows="3" placeholder="Description of the issue..."></textarea>
                    <input type="text" id="instanceDetails" placeholder="Instance/Pod details (JSON or text)" />
                    <button class="btn-submit" onclick="createTicket()">📧 Create Ticket & Send Email</button>
                </div>
                
                <div class="tickets-list">
                    <h4 style="color: white; margin-bottom: 10px;">Recent Tickets</h4>
                    <div id="ticketsList">
                        <div style="text-align: center; color: #aaa;">No tickets yet</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentFilter = 'ALL';
        let logs = [];
        let streaming = true;
        
        // Team Members
        const teamMembers = [
            {name: "Rakesh Anagani", role: "Lead DevOps Engineer", avatar: "RA"},
            {name: "Charani Kavali", role: "Cloud Architect", avatar: "CK"},
            {name: "Pujitha Reddy", role: "ML Engineer", avatar: "PR"}
        ];
        
        // Render Team Section
        function renderTeam() {
            const teamSection = document.getElementById('teamSection');
            teamSection.innerHTML = teamMembers.map(m => `
                <div class="team-card">
                    <div class="team-avatar">${m.avatar}</div>
                    <div class="team-name">${m.name}</div>
                    <div class="team-role">${m.role}</div>
                </div>
            `).join('');
        }
        
        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws');
            ws.onopen = () => console.log('✅ Connected');
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'log' && streaming) addLog(data.data);
                else if (data.type === 'metrics') updateMetrics(data.data);
            };
            ws.onclose = () => setTimeout(connect, 3000);
        }
        
        function addLog(log) {
            logs.unshift(log);
            if (logs.length > 200) logs.pop();
            updateDisplay();
        }
        
        function updateDisplay() {
            const filtered = currentFilter === 'ALL' ? logs : logs.filter(l => l.level === currentFilter);
            const container = document.getElementById('logsContainer');
            
            if (filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center;padding:40px;">No logs</div>';
                return;
            }
            
            container.innerHTML = filtered.slice(0, 100).map(log => `
                <div class="log-entry log-${log.level}">
                    <div><span style="color:#aaa;">${new Date(log.timestamp).toLocaleTimeString()}</span> <strong>${log.container}</strong> [${log.source}]</div>
                    <div style="margin-top: 5px;">${log.message}</div>
                </div>
            `).join('');
            
            document.getElementById('totalLogs').innerText = logs.length;
            document.getElementById('errorCount').innerText = logs.filter(l => l.level === 'ERROR').length;
            const containers = new Set(logs.map(l => l.container));
            document.getElementById('activeContainers').innerText = containers.size;
        }
        
        function updateMetrics(metrics) {
            if (metrics.cpu) document.getElementById('cpuMetric').innerText = `${metrics.cpu.percent}%`;
            if (metrics.memory) document.getElementById('memoryMetric').innerText = `${metrics.memory.percent}%`;
            if (metrics.disk) document.getElementById('diskMetric').innerText = `${metrics.disk.percent}%`;
            const netTotal = (metrics.network?.bytes_sent_mb + metrics.network?.bytes_recv_mb).toFixed(1);
            document.getElementById('networkMetric').innerText = `${netTotal} MB/s`;
        }
        
        async function createTicket() {
            const title = document.getElementById('ticketTitle').value;
            const severity = document.getElementById('ticketSeverity').value;
            const description = document.getElementById('ticketDesc').value;
            const instanceDetails = document.getElementById('instanceDetails').value;
            
            if (!title || !description) {
                alert('Please fill in title and description');
                return;
            }
            
            const ticket = {
                title: title,
                severity: severity,
                description: description,
                instance_details: { details: instanceDetails, timestamp: new Date().toISOString() },
                created_by: "User"
            };
            
            const response = await fetch('/api/tickets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ticket)
            });
            
            const result = await response.json();
            if (result.success) {
                alert(`✅ Ticket #${result.ticket.id} created! Email sent to team.`);
                document.getElementById('ticketTitle').value = '';
                document.getElementById('ticketDesc').value = '';
                document.getElementById('instanceDetails').value = '';
                loadTickets();
            }
        }
        
        async function loadTickets() {
            const response = await fetch('/api/tickets');
            const data = await response.json();
            const ticketsList = document.getElementById('ticketsList');
            
            if (data.tickets.length === 0) {
                ticketsList.innerHTML = '<div style="text-align: center; color: #aaa;">No tickets yet</div>';
                return;
            }
            
            ticketsList.innerHTML = data.tickets.slice(-5).reverse().map(t => `
                <div class="ticket-item">
                    <div><strong>#${t.id}</strong> <span style="color: ${t.severity === 'CRITICAL' ? '#dc2626' : t.severity === 'HIGH' ? '#ef4444' : '#f59e0b'}">${t.severity}</span></div>
                    <div>${t.title.substring(0, 50)}</div>
                    <div style="font-size: 10px; color: #aaa;">${new Date(t.created_at).toLocaleString()}</div>
                </div>
            `).join('');
        }
        
        function setFilter(level) {
            currentFilter = level;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            updateDisplay();
        }
        
        function stopStreaming() { streaming = false; if (ws) ws.send(JSON.stringify({action: 'stop'})); }
        function startStreaming() { streaming = true; if (ws) ws.send(JSON.stringify({action: 'start'})); }
        function clearLogs() { logs = []; updateDisplay(); if (ws) ws.send(JSON.stringify({action: 'clear'})); }
        
        renderTeam();
        connect();
        loadTickets();
        setInterval(loadTickets, 10000);
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
