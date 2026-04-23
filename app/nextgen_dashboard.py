"""
NextGen LogIQ Dashboard - Cloud-Ready for AWS EKS
Enhanced with production features for Kubernetes deployment
"""
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import random
import smtplib
import os
import socket
import platform
import psutil
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict, deque
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Cloud Environment Detection ====================
POD_NAME = os.getenv("HOSTNAME", socket.gethostname())
POD_IP = os.getenv("POD_IP", socket.gethostbyname(socket.gethostname()))
NAMESPACE = os.getenv("NAMESPACE", "default")
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "aws")
REGION = os.getenv("AWS_REGION", "us-east-1")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

print(f"""
╔══════════════════════════════════════════════════════════════╗
║     NextGen LogIQ Dashboard - Cloud Deployment Mode        ║
╠══════════════════════════════════════════════════════════════╣
║  Pod Name: {POD_NAME:<40} ║
║  Pod IP:   {POD_IP:<40} ║
║  Namespace:{NAMESPACE:<40} ║
║  Region:   {REGION:<40} ║
║  Environment: {ENVIRONMENT:<40} ║
╚══════════════════════════════════════════════════════════════╝
""")

# ==================== Email Configuration ====================
TEAM_MEMBERS = [
    {"name": "DevOps Team", "email": os.getenv("ALERT_EMAIL", "devops@example.com")},
    {"name": "SRE Team", "email": os.getenv("SRE_EMAIL", "sre@example.com")}
]

SMTP_CONFIG = {
    "server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "username": os.getenv("EMAIL_USER", ""),
    "password": os.getenv("EMAIL_PASS", ""),
    "enabled": False
}

if SMTP_CONFIG["username"] and SMTP_CONFIG["password"]:
    SMTP_CONFIG["enabled"] = True
    print("✅ Email notifications ENABLED")
else:
    print("⚠️ Email notifications DISABLED - Set EMAIL_USER and EMAIL_PASS")

# ==================== Real Kubernetes API Integration ====================
def get_real_kubernetes_pods():
    """Fetch real pods from Kubernetes API if running in cluster"""
    try:
        # Try to load in-cluster config
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        v1 = client.CoreV1Api()
        pods = v1.list_pod_for_all_namespaces(watch=False)
        
        containers = []
        for pod in pods.items:
            if pod.status.phase == "Running":
                for container in pod.spec.containers:
                    # Calculate mock metrics (in real scenario, get from metrics API)
                    containers.append({
                        "name": pod.metadata.name,
                        "image": container.image,
                        "status": pod.status.phase,
                        "cpu": random.randint(10, 80),
                        "memory": random.randint(20, 90),
                        "node": pod.spec.node_name or "unknown",
                        "namespace": pod.metadata.namespace,
                        "latency": random.randint(10, 200),
                        "restarts": sum([s.restart_count for s in pod.status.container_statuses]) if pod.status.container_statuses else 0
                    })
        return containers if containers else MOCK_CONTAINERS
    except Exception as e:
        print(f"⚠️ Cannot connect to Kubernetes API: {e}. Using mock data.")
        return MOCK_CONTAINERS

# ==================== Real AWS Metrics (Optional) ====================
def get_real_aws_metrics():
    """Fetch real metrics from AWS CloudWatch"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        cloudwatch = boto3.client('cloudwatch', region_name=REGION)
        
        # Get CPU utilization for EKS cluster
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/ECS',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'ClusterName', 'Value': os.getenv('EKS_CLUSTER_NAME', 'logiq-cluster')}],
            StartTime=datetime.utcnow() - timedelta(minutes=5),
            EndTime=datetime.utcnow(),
            Period=300,
            Statistics=['Average']
        )
        
        if response['Datapoints']:
            cpu = response['Datapoints'][0]['Average']
        else:
            cpu = random.randint(20, 60)
            
        return {
            'cpu': cpu,
            'memory': random.randint(40, 80),
            'disk': random.randint(30, 70),
            'network_mb': round(random.uniform(10, 50), 1),
            'pod_count': len(MOCK_CONTAINERS),
            'uptime': random.randint(1, 60),
            'avg_latency': random.randint(50, 300),
            'error_rate': random.randint(0, 20)
        }
    except Exception as e:
        print(f"⚠️ Cannot fetch AWS metrics: {e}. Using mock data.")
        return get_system_metrics()

def get_real_aws_billing():
    """Fetch real billing data from AWS Cost Explorer"""
    try:
        import boto3
        ce = boto3.client('ce', region_name='us-east-1')
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=14)
        
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        daily_costs = []
        total_cost = 0
        
        for day in response['ResultsByTime']:
            cost = float(day['Total']['BlendedCost']['Amount'])
            total_cost += cost
            daily_costs.append({
                'date': day['TimePeriod']['Start'],
                'cost': round(cost, 2)
            })
        
        services = []
        for group in response['ResultsByTime'][0]['Groups']:
            services.append({
                'name': group['Keys'][0],
                'cost': round(float(group['Metrics']['BlendedCost']['Amount']), 2)
            })
        
        return {
            'total': round(total_cost, 2),
            'daily': daily_costs,
            'services': services[:5],
            'currency': 'USD',
            'is_real': True
        }
    except Exception as e:
        print(f"⚠️ Cannot fetch AWS billing: {e}. Using mock data.")
        return get_aws_billing()

# ==================== Mock Data (Fallback) ====================
MOCK_CONTAINERS = [
    {"name": "logiq-api-pod-1", "image": "logiq/api:latest", "status": "Running", "cpu": 32, "memory": 45, "node": "eks-node-1", "namespace": "logiq-prod", "latency": 45},
    {"name": "logiq-worker-pod-1", "image": "logiq/worker:latest", "status": "Running", "cpu": 56, "memory": 67, "node": "eks-node-2", "namespace": "logiq-prod", "latency": 78},
    {"name": "logiq-db-pod-1", "image": "postgres:15", "status": "Running", "cpu": 18, "memory": 52, "node": "eks-node-3", "namespace": "logiq-prod", "latency": 23},
    {"name": "logiq-redis-1", "image": "redis:7", "status": "Running", "cpu": 12, "memory": 34, "node": "eks-node-1", "namespace": "logiq-prod", "latency": 12},
    {"name": "logiq-kibana-1", "image": "kibana:8", "status": "Running", "cpu": 25, "memory": 41, "node": "eks-node-4", "namespace": "logiq-prod", "latency": 56},
    {"name": "logiq-postgres-1", "image": "postgres:15", "status": "Running", "cpu": 22, "memory": 58, "node": "eks-node-2", "namespace": "logiq-prod", "latency": 34},
    {"name": "logiq-qdrant-1", "image": "qdrant/qdrant", "status": "Running", "cpu": 38, "memory": 62, "node": "eks-node-4", "namespace": "logiq-prod", "latency": 89},
]

# ==================== Anomaly Detection ====================
error_rate_history = deque(maxlen=100)
anomaly_threshold = 1.5

def detect_anomaly(current_rate):
    if len(error_rate_history) < 10:
        error_rate_history.append(current_rate)
        return False
    
    avg_rate = sum(error_rate_history) / len(error_rate_history)
    std_dev = (sum((x - avg_rate) ** 2 for x in error_rate_history) / len(error_rate_history)) ** 0.5
    
    if std_dev > 0:
        z_score = (current_rate - avg_rate) / std_dev
        error_rate_history.append(current_rate)
        return z_score > anomaly_threshold
    error_rate_history.append(current_rate)
    return False

# ==================== Ticket Storage ====================
tickets = []
ticket_id_counter = 1
alert_history = []

# ==================== System Metrics ====================
def get_system_metrics():
    # Try to get real system metrics if running locally
    try:
        return {
            'cpu': psutil.cpu_percent(),
            'memory': psutil.virtual_memory().percent,
            'disk': psutil.disk_usage('/').percent,
            'network_mb': round(psutil.net_io_counters().bytes_recv / 1024 / 1024, 1),
            'pod_count': len(MOCK_CONTAINERS),
            'uptime': int((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds() / 3600),
            'avg_latency': random.randint(50, 200),
            'error_rate': random.randint(0, 15)
        }
    except:
        # Fallback to mock
        return {
            'cpu': random.randint(3, 25),
            'memory': random.randint(55, 85),
            'disk': random.randint(40, 70),
            'network_mb': round(random.uniform(5, 25), 1),
            'pod_count': len(MOCK_CONTAINERS),
            'uptime': random.randint(1, 30),
            'avg_latency': random.randint(50, 200),
            'error_rate': random.randint(0, 15)
        }

def get_aws_billing():
    daily = []
    total = 0
    for i in range(15):
        cost = round(85 + (i % 7) * 5 + random.uniform(-10, 15), 2)
        total += cost
        daily.append({'date': (datetime.now() - timedelta(days=14-i)).strftime('%Y-%m-%d'), 'cost': cost})
    
    return {
        'total': round(total, 2),
        'daily': daily,
        'services': [
            {'name': 'EC2', 'cost': round(total * 0.35, 2)},
            {'name': 'EKS', 'cost': round(total * 0.25, 2)},
            {'name': 'Lambda', 'cost': round(total * 0.15, 2)},
            {'name': 'RDS', 'cost': round(total * 0.12, 2)},
            {'name': 'S3', 'cost': round(total * 0.08, 2)},
        ],
        'currency': 'USD',
        'is_real': False
    }

# ==================== Log Generator ====================
def generate_log():
    # Try to get real pods if in Kubernetes
    containers = get_real_kubernetes_pods() if os.getenv("KUBERNETES_SERVICE_HOST") else MOCK_CONTAINERS
    container = random.choice(containers)
    
    services = ['api-gateway', 'auth-svc', 'payment-svc', 'log-processor', 'notification-svc']
    error_messages = {
        'ERROR': [
            f"Database connection pool exhausted on {container['name']}",
            f"Timeout connecting to downstream service from {container['name']}",
            f"Authentication failed: Invalid credentials on {container['name']}",
            f"Rate limit exceeded (429) on {container['name']}",
            f"SSL handshake failed on {container['name']}"
        ],
        'WARNING': [
            f"High CPU usage: {container['cpu']}% on {container['name']}",
            f"Memory pressure detected: {container['memory']}% used",
            f"Slow query execution > 5s on {container['name']}",
            f"Retry attempts: 3/5 on {container['name']}"
        ],
        'INFO': [
            f"Successfully connected to database from {container['name']}",
            f"Cache hit ratio: {random.randint(75, 95)}%",
            f"Processed {random.randint(1000, 5000)} requests",
            f"Health check: OK on {container['name']}"
        ],
        'CRITICAL': [
            f"CRITICAL: {container['name']} is in CrashLoopBackOff state",
            f"Data corruption detected in volume mounted to {container['name']}",
            f"OOMKilled: Process terminated on {container['name']}",
            f"Node {container['node']} is unreachable"
        ]
    }
    
    rand = random.random()
    if rand < 0.55: level = 'INFO'
    elif rand < 0.75: level = 'WARNING'
    elif rand < 0.92: level = 'ERROR'
    else: level = 'CRITICAL'
    
    return {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "pod": container['name'],
        "image": container['image'],
        "service": random.choice(services),
        "message": random.choice(error_messages[level]),
        "namespace": container.get('namespace', 'default'),
        "node": container.get('node', 'unknown'),
        "region": REGION,
        "trace_id": f"trace-{random.randint(1000, 9999)}",
        "cloud_provider": CLOUD_PROVIDER
    }

# ==================== WebSocket ====================
logs = []
connected_clients = []
streaming = True

async def broadcast(data):
    for client in connected_clients[:]:
        try:
            await client.send_text(json.dumps(data))
        except:
            if client in connected_clients:
                connected_clients.remove(client)

async def log_loop():
    global streaming
    error_count_last_minute = 0
    
    while True:
        if streaming and connected_clients:
            log = generate_log()
            logs.insert(0, log)
            
            if log['level'] in ['ERROR', 'CRITICAL']:
                error_count_last_minute += 1
            
            if len(logs) > 500:
                logs.pop()
            
            await broadcast({"type": "log", "data": log})
            
            if log['level'] == 'CRITICAL':
                await auto_create_ticket(log)
                await broadcast({"type": "alert", "data": {"message": f"🚨 CRITICAL: {log['message'][:50]}", "severity": "critical"}})
            
            if len(logs) % 30 == 0:
                current_rate = error_count_last_minute
                if detect_anomaly(current_rate):
                    await broadcast({"type": "anomaly", "data": {"message": "⚠️ Unusual error rate detected!", "rate": current_rate}})
                error_count_last_minute = 0
                
        await asyncio.sleep(0.6)

async def metrics_loop():
    while True:
        if connected_clients:
            # Try to get real metrics if AWS credentials are available
            try:
                import boto3
                metrics = get_real_aws_metrics()
                billing = get_real_aws_billing()
            except:
                metrics = get_system_metrics()
                billing = get_aws_billing()
            
            await broadcast({"type": "metrics", "data": metrics})
            await broadcast({"type": "billing", "data": billing})
            
            # Get real pods if in Kubernetes
            if os.getenv("KUBERNETES_SERVICE_HOST"):
                containers = get_real_kubernetes_pods()
            else:
                containers = MOCK_CONTAINERS
            
            await broadcast({"type": "containers", "data": containers})
        await asyncio.sleep(4)

async def auto_create_ticket(log):
    global ticket_id_counter
    ticket = {
        "id": ticket_id_counter,
        "title": f"Auto: {log['level']} on {log['pod']}",
        "description": log['message'],
        "severity": log['level'],
        "instance": log['pod'],
        "instance_details": {"pod": log['pod'], "namespace": log['namespace'], "node": log['node']},
        "created_by": "Auto-Detection",
        "created_at": datetime.now().isoformat(),
        "status": "OPEN",
        "cloud_region": REGION
    }
    tickets.append(ticket)
    send_email_notification(ticket)
    print(f"🎫 Auto-created ticket #{ticket['id']}: {ticket['title']}")
    await broadcast({"type": "new_ticket", "data": ticket})
    ticket_id_counter += 1

def send_email_notification(ticket: Dict):
    if not SMTP_CONFIG["enabled"]:
        print(f"📧 [SIMULATED] Email for Ticket #{ticket['id']}")
        return True
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = SMTP_CONFIG["username"]
        msg['To'] = ", ".join([m["email"] for m in TEAM_MEMBERS])
        msg['Subject'] = f"[LogIQ] 🚨 {ticket['severity']} Ticket #{ticket['id']} - {POD_NAME}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background: #ea580c; color: white; padding: 20px; }}
            .ticket {{ border: 1px solid #ddd; padding: 15px; margin: 10px; }}
            .critical {{ color: #dc2626; }}
        </style></head>
        <body>
            <div class="header">
                <h2>🔍 LogIQ Alert - {ENVIRONMENT}</h2>
                <p>Pod: {POD_NAME} | Region: {REGION}</p>
            </div>
            <div class="ticket">
                <h3>Ticket #{ticket['id']} - {ticket['severity']}</h3>
                <p><strong>Title:</strong> {ticket['title']}</p>
                <p><strong>Description:</strong> {ticket['description']}</p>
                <p><strong>Instance:</strong> {ticket['instance']}</p>
                <p><strong>Time:</strong> {ticket['created_at']}</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(SMTP_CONFIG["server"], SMTP_CONFIG["port"]) as server:
            server.starttls()
            server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
            server.send_message(msg)
        print(f"✅ Email sent for Ticket #{ticket['id']}")
        return True
    except Exception as e:
        print(f"❌ Email error: {str(e)}")
        return False

@app.on_event("startup")
async def startup():
    print("\n" + "=" * 70)
    print("🚀 NEXTGEN LOGIQ DASHBOARD - Cloud Native Edition")
    print("=" * 70)
    print(f"📍 Running on: {POD_NAME} ({POD_IP})")
    print(f"☁️  Cloud Provider: {CLOUD_PROVIDER}")
    print(f"🌍 Region: {REGION}")
    print(f"🔧 Environment: {ENVIRONMENT}")
    print("=" * 70 + "\n")
    asyncio.create_task(log_loop())
    asyncio.create_task(metrics_loop())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"🔌 Client connected. Total: {len(connected_clients)}")
    
    for log in logs[-50:]:
        await websocket.send_text(json.dumps({"type": "log", "data": log}))
    await websocket.send_text(json.dumps({"type": "containers", "data": MOCK_CONTAINERS}))
    await websocket.send_text(json.dumps({"type": "billing", "data": get_aws_billing()}))
    
    try:
        while True:
            await websocket.receive_text()
    except:
        connected_clients.remove(websocket)
        print(f"🔌 Client disconnected. Total: {len(connected_clients)}")

# ==================== API Endpoints ====================
@app.get("/")
async def root():
    return HTMLResponse(HTML)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "pod": POD_NAME,
        "ip": POD_IP,
        "namespace": NAMESPACE,
        "region": REGION,
        "environment": ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(connected_clients),
        "total_logs": len(logs),
        "total_tickets": len(tickets)
    }

@app.get("/metrics")
async def metrics_endpoint():
    return {
        "pod_name": POD_NAME,
        "pod_ip": POD_IP,
        "namespace": NAMESPACE,
        "region": REGION,
        "active_connections": len(connected_clients),
        "total_logs": len(logs),
        "total_tickets": len(tickets),
        "error_logs": len([l for l in logs if l['level'] in ['ERROR', 'CRITICAL']]),
        "uptime_seconds": (datetime.now() - startup_time).total_seconds() if 'startup_time' in globals() else 0
    }

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get('message', '').lower()
    metrics = get_system_metrics()
    billing = get_aws_billing()
    
    responses = []
    
    if any(word in message for word in ['instance', 'pod', 'container']):
        containers = get_real_kubernetes_pods() if os.getenv("KUBERNETES_SERVICE_HOST") else MOCK_CONTAINERS
        responses.append(f"📦 **Active Pods in {NAMESPACE}:**")
        for c in containers[:5]:
            responses.append(f"   • `{c['name']}` - CPU: {c['cpu']}%, Memory: {c['memory']}%")
    
    if any(word in message for word in ['error', 'critical', 'problem']):
        error_logs = [l for l in logs if l['level'] in ['ERROR', 'CRITICAL']][:5]
        if error_logs:
            responses.append("🔴 **Recent Errors/Critical:**")
            for e in error_logs:
                responses.append(f"   • [{e['level']}] {e['pod']}: {e['message'][:60]}")
        else:
            responses.append("✅ No errors detected!")
    
    if 'cpu' in message:
        responses.append(f"💻 **CPU Usage:** {metrics['cpu']}%")
    
    if 'memory' in message or 'ram' in message:
        responses.append(f"🧠 **Memory Usage:** {metrics['memory']}%")
    
    if any(word in message for word in ['cost', 'billing']):
        responses.append(f"💰 **Monthly AWS Cost:** ${billing['total']:,.2f}")
    
    if 'pod' in message and 'info' in message:
        responses.append(f"📋 **Current Pod Info:**\n   • Name: {POD_NAME}\n   • IP: {POD_IP}\n   • Namespace: {NAMESPACE}\n   • Region: {REGION}")
    
    if not responses:
        responses = [
            "🤖 **AI Assistant**",
            f"📍 Running on: {POD_NAME}",
            "Ask me about:",
            "• 'Show errors' - Recent errors",
            "• 'CPU/Memory usage' - System metrics",
            "• 'Pods/Instances' - Container status",
            "• 'AWS cost' - Billing info",
            "• 'Pod info' - Current deployment details"
        ]
    
    return {"reply": "\n".join(responses)}

@app.post("/api/tickets")
async def create_ticket(request: Request):
    global ticket_id_counter
    data = await request.json()
    ticket = {
        "id": ticket_id_counter,
        "title": data.get('title'),
        "description": data.get('description'),
        "severity": data.get('severity', 'MEDIUM'),
        "instance": data.get('instance', POD_NAME),
        "created_by": data.get('created_by', 'User'),
        "created_at": datetime.now().isoformat(),
        "status": "OPEN",
        "cloud_region": REGION
    }
    tickets.append(ticket)
    send_email_notification(ticket)
    await broadcast({"type": "new_ticket", "data": ticket})
    ticket_id_counter += 1
    return {"success": True, "ticket": ticket}

@app.get("/api/tickets")
async def get_tickets():
    return {"tickets": tickets[-20:]}

@app.get("/api/billing")
async def get_billing():
    try:
        import boto3
        return get_real_aws_billing()
    except:
        return get_aws_billing()

@app.get("/api/containers")
async def get_containers():
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return {"containers": get_real_kubernetes_pods()}
    return {"containers": MOCK_CONTAINERS}

@app.get("/api/metrics")
async def get_metrics():
    try:
        import boto3
        return get_real_aws_metrics()
    except:
        return get_system_metrics()

@app.get("/api/logs/export")
async def export_logs():
    return {"logs": logs[:100], "pod_info": {"name": POD_NAME, "ip": POD_IP, "namespace": NAMESPACE}}

# ==================== Enhanced HTML Dashboard ====================
startup_time = datetime.now()

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogIQ - Cloud Native Log Analysis System</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
            color: #1c1917;
            padding: 20px;
            transition: background 0.3s;
        }
        
        body.dark-mode {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e2e8f0;
        }
        
        body.dark-mode .stat-card,
        body.dark-mode .logs-panel,
        body.dark-mode .chat-panel,
        body.dark-mode .billing-panel,
        body.dark-mode .tickets-panel {
            background: #1e293b;
            border-color: #334155;
        }
        
        .header {
            background: linear-gradient(135deg, #ea580c 0%, #f97316 50%, #fb923c 100%);
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 24px;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .cloud-badge {
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-family: monospace;
        }
        
        .theme-toggle {
            background: rgba(255,255,255,0.2);
            border: none;
            padding: 10px 16px;
            border-radius: 10px;
            cursor: pointer;
            color: white;
            font-size: 18px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .stat-card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #fed7aa;
            transition: transform 0.2s;
        }
        
        .stat-card:hover { transform: translateY(-2px); }
        .stat-value { font-size: 32px; font-weight: bold; color: #ea580c; }
        .stat-label { font-size: 12px; color: #78716c; margin-top: 8px; font-weight: 500; }
        
        .main-layout {
            display: grid;
            grid-template-columns: 1fr 400px;
            gap: 24px;
        }
        
        .logs-panel {
            background: white;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #fed7aa;
        }
        
        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }
        
        .filter-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .filter-btn {
            padding: 6px 14px;
            border: 1px solid #fed7aa;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .filter-btn:hover { background: #fff7ed; border-color: #fb923c; }
        .filter-btn.active { background: #ea580c; color: white; border-color: #ea580c; }
        
        .log-list {
            max-height: 550px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .log-item {
            padding: 12px;
            border-radius: 10px;
            border-left: 4px solid;
            background: #fefce8;
            transition: all 0.2s;
            cursor: pointer;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .log-CRITICAL {
            border-left-color: #dc2626;
            background: #fef2f2;
            animation: pulse-red 1s;
        }
        
        @keyframes pulse-red {
            0%, 100% { background: #fef2f2; }
            50% { background: #fee2e2; }
        }
        
        .log-ERROR { border-left-color: #ef4444; background: #fef2f2; }
        .log-WARNING { border-left-color: #f59e0b; background: #fffbeb; }
        .log-INFO { border-left-color: #10b981; background: #f0fdf4; }
        
        .log-header { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 11px; }
        .log-time { color: #78716c; font-weight: 500; }
        .log-pod { background: #fed7aa; padding: 2px 8px; border-radius: 6px; font-family: monospace; font-size: 10px; font-weight: 600; }
        .log-level { font-weight: 700; font-size: 11px; }
        .log-CRITICAL .log-level { color: #dc2626; }
        .log-ERROR .log-level { color: #ef4444; }
        .log-message { font-size: 13px; color: #1c1917; margin-bottom: 6px; word-break: break-word; font-weight: 500; }
        .log-meta { font-size: 10px; color: #a8a29e; font-family: monospace; }
        
        .right-panel { display: flex; flex-direction: column; gap: 20px; }
        .chat-panel, .billing-panel, .tickets-panel {
            background: white;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #fed7aa;
        }
        
        .chat-messages {
            height: 250px;
            overflow-y: auto;
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .message {
            padding: 10px 14px;
            border-radius: 12px;
            max-width: 90%;
            word-wrap: break-word;
            font-size: 13px;
        }
        
        .user-message { background: #ea580c; color: white; align-self: flex-end; }
        .bot-message { background: #fff7ed; color: #431407; align-self: flex-start; border: 1px solid #fed7aa; }
        
        .chat-input-area { display: flex; gap: 10px; }
        .chat-input { flex: 1; padding: 10px 14px; border: 1px solid #fed7aa; border-radius: 10px; font-size: 13px; }
        .voice-btn { background: #ef4444; border: none; width: 42px; border-radius: 10px; cursor: pointer; color: white; }
        .voice-btn.recording { animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        
        .send-btn { background: #ea580c; color: white; border: none; padding: 0 18px; border-radius: 10px; cursor: pointer; font-weight: 600; }
        .btn-primary { background: #ea580c; color: white; padding: 10px 20px; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; width: 100%; }
        .btn-danger { background: #ef4444; color: white; padding: 8px 16px; border: none; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600; }
        
        .alert-toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc2626;
            color: white;
            padding: 12px 20px;
            border-radius: 10px;
            font-weight: 600;
            z-index: 1000;
            animation: slideInRight 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .connection-status {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #ea580c;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            color: white;
            font-weight: 600;
        }
        
        .ticket-item {
            background: #fff7ed;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            border-left: 3px solid;
            cursor: pointer;
        }
        
        .export-buttons { display: flex; gap: 10px; margin-top: 10px; }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #fed7aa; border-radius: 3px; }
        ::-webkit-scrollbar-thumb { background: #fb923c; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🔍 LogIQ Cloud Native Log Analysis</h1>
            <p>AWS EKS | Real-time Monitoring | AI Chatbot | Anomaly Detection</p>
        </div>
        <div style="display: flex; gap: 10px;">
            <div class="cloud-badge" id="podInfo">Loading...</div>
            <button class="theme-toggle" onclick="toggleTheme()">🌓 Dark/Light</button>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-value" id="totalLogs">0</div><div class="stat-label">📊 Total Logs</div></div>
        <div class="stat-card"><div class="stat-value" id="errorCount">0</div><div class="stat-label">🔴 Errors & Critical</div></div>
        <div class="stat-card"><div class="stat-value" id="podCount">0</div><div class="stat-label">🖥️ Active Pods</div></div>
        <div class="stat-card"><div class="stat-value" id="cpuStat">0%</div><div class="stat-label">⚡ CPU Usage</div></div>
        <div class="stat-card"><div class="stat-value" id="memoryStat">0%</div><div class="stat-label">🧠 Memory Usage</div></div>
        <div class="stat-card"><div class="stat-value" id="errorRateStat">0</div><div class="stat-label">📈 Error Rate (per min)</div></div>
    </div>
    
    <div class="main-layout">
        <div class="logs-panel">
            <div class="logs-header">
                <h3>📋 Live Log Stream</h3>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="setFilter('ALL')">All</button>
                    <button class="filter-btn" onclick="setFilter('ERROR')">🔴 Error</button>
                    <button class="filter-btn" onclick="setFilter('WARNING')">🟡 Warning</button>
                    <button class="filter-btn" onclick="setFilter('INFO')">🔵 Info</button>
                    <button class="filter-btn" onclick="setFilter('CRITICAL')">🔴 Critical</button>
                </div>
            </div>
            <div class="log-list" id="logList"><div class="text-muted">⏳ Waiting for logs...</div></div>
            <div class="export-buttons">
                <button class="btn-danger" onclick="stopStreaming()">⏹️ Stop</button>
                <button class="btn-primary" onclick="startStreaming()" style="background:#059669;">▶️ Start</button>
                <button class="btn-primary" onclick="exportLogs()" style="background:#3b82f6;">📎 Export Logs</button>
            </div>
        </div>
        
        <div class="right-panel">
            <div class="chat-panel">
                <h3>🤖 AI Assistant <span style="font-size:11px;">(Voice Enabled)</span></h3>
                <div class="chat-messages" id="chatMessages">
                    <div class="message bot-message">👋 Hello! I'm running on AWS EKS. Ask me about errors, pods, CPU, memory, or AWS costs.</div>
                </div>
                <div class="chat-input-area">
                    <input type="text" class="chat-input" id="chatInput" placeholder="Ask me anything..." onkeypress="if(event.key==='Enter') sendMessage()">
                    <button class="voice-btn" id="voiceBtn" onclick="toggleVoice()">🎤</button>
                    <button class="send-btn" onclick="sendMessage()">Send</button>
                </div>
            </div>
            
            <div class="billing-panel">
                <h3>💰 AWS Billing</h3>
                <div class="stat-value" id="billingTotal">$0</div>
                <canvas id="billingChart" style="height:120px; margin:10px 0;"></canvas>
                <div id="serviceList"></div>
            </div>
            
            <div class="tickets-panel">
                <h3>🎫 Create Support Ticket</h3>
                <input type="text" id="ticketTitle" placeholder="Ticket Title">
                <select id="ticketSeverity">
                    <option value="LOW">🔵 Low</option>
                    <option value="MEDIUM">🟡 Medium</option>
                    <option value="HIGH">🟠 High</option>
                    <option value="CRITICAL">🔴 Critical</option>
                </select>
                <textarea id="ticketDesc" rows="2" placeholder="Description"></textarea>
                <button class="btn-primary" onclick="createTicket()">📧 Create Ticket & Send Email</button>
                <div id="recentTickets" style="margin-top:15px;"></div>
            </div>
        </div>
    </div>
    <div class="connection-status" id="connStatus">🟢 Connected</div>
    
    <script>
        let ws = null;
        let filter = 'ALL';
        let logs = [];
        let streaming = true;
        let billingChart = null;
        let recognition = null;
        let errorCount = 0;
        
        // Fetch pod info on load
        async function loadPodInfo() {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                document.getElementById('podInfo').innerHTML = `☁️ ${data.pod} | ${data.region}`;
            } catch(e) {
                document.getElementById('podInfo').innerHTML = `☁️ AWS EKS`;
            }
        }
        
        function toggleTheme() {
            document.body.classList.toggle('dark-mode');
        }
        
        function showAlert(message, severity = 'error') {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert-toast';
            alertDiv.innerHTML = severity === 'critical' ? '🔴 ' + message : '⚠️ ' + message;
            document.body.appendChild(alertDiv);
            setTimeout(() => alertDiv.remove(), 5000);
        }
        
        function initVoice() {
            if ('webkitSpeechRecognition' in window) {
                recognition = new webkitSpeechRecognition();
                recognition.continuous = false;
                recognition.lang = 'en-US';
                recognition.onresult = (event) => {
                    document.getElementById('chatInput').value = event.results[0][0].transcript;
                    sendMessage();
                };
                recognition.onend = () => {
                    document.getElementById('voiceBtn')?.classList.remove('recording');
                };
            }
        }
        
        function toggleVoice() {
            if (!recognition) {
                showAlert("Voice recognition not supported");
                return;
            }
            recognition.start();
            document.getElementById('voiceBtn').classList.add('recording');
        }
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws');
            ws.onopen = () => document.getElementById('connStatus').innerHTML = '🟢 Connected';
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'log' && streaming) addLog(data.data);
                else if (data.type === 'metrics') updateMetrics(data.data);
                else if (data.type === 'billing') updateBilling(data.data);
                else if (data.type === 'containers') updatePodCount(data.data);
                else if (data.type === 'new_ticket') addTicketToList(data.data);
                else if (data.type === 'alert') showAlert(data.data.message, data.data.severity);
                else if (data.type === 'anomaly') showAlert(data.data.message + ' Rate: ' + data.data.rate);
            };
            ws.onclose = () => setTimeout(connect, 3000);
        }
        
        function addLog(log) {
            logs.unshift(log);
            if (logs.length > 500) logs.pop();
            renderLogs();
            updateStats();
            
            if (log.level === 'CRITICAL') {
                showAlert('CRITICAL: ' + log.message.substring(0, 60), 'critical');
            } else if (log.level === 'ERROR') {
                showAlert('🔴 ERROR: ' + log.message.substring(0, 60), 'error');
            }
        }
        
        function renderLogs() {
            const filtered = filter === 'ALL' ? logs : logs.filter(l => l.level === filter);
            const container = document.getElementById('logList');
            
            if (filtered.length === 0) {
                container.innerHTML = '<div class="text-muted">📭 No logs to display</div>';
                return;
            }
            
            container.innerHTML = filtered.slice(0, 80).map(log => {
                const time = new Date(log.timestamp).toLocaleTimeString();
                const levelIcon = log.level === 'ERROR' ? '🔴' : log.level === 'CRITICAL' ? '🔴'  : log.level === 'WARNING' ? '⚠️' : 'ℹ️';
                return `
                    <div class="log-item log-${log.level}" onclick="quickCreateTicket('${log.pod}', '${escapeHtml(log.message).replace(/'/g, "\\\\'")}', '${log.level}')">
                        <div class="log-header">
                            <span class="log-time">🕐 ${time}</span>
                            <span class="log-pod">📦 ${log.pod}</span>
                            <span class="log-level">${levelIcon} ${log.level}</span>
                        </div>
                        <div class="log-message">[${log.service}] ${escapeHtml(log.message)}</div>
                        <div class="log-meta">📍 ${log.node} | 🏷️ ${log.namespace} | 🔑 ${log.trace_id} | ☁️ ${log.cloud_provider || 'aws'}</div>
                    </div>
                `;
            }).join('');
        }
        
        function updateStats() {
            document.getElementById('totalLogs').innerText = logs.length;
            const errors = logs.filter(l => l.level === 'ERROR' || l.level === 'CRITICAL').length;
            document.getElementById('errorCount').innerText = errors;
        }
        
        function updateMetrics(metrics) {
            document.getElementById('cpuStat').innerHTML = `${Math.round(metrics.cpu)}%`;
            document.getElementById('memoryStat').innerHTML = `${Math.round(metrics.memory)}%`;
            document.getElementById('errorRateStat').innerHTML = metrics.error_rate;
        }
        
        function updatePodCount(containers) {
            document.getElementById('podCount').innerText = containers.length;
        }
        
        function updateBilling(billing) {
            document.getElementById('billingTotal').innerHTML = `$${billing.total.toLocaleString()}`;
            
            if (billingChart) billingChart.destroy();
            const ctx = document.getElementById('billingChart').getContext('2d');
            billingChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: billing.daily.map(d => d.date.slice(5)),
                    datasets: [{
                        label: 'Daily Cost (USD)',
                        data: billing.daily.map(d => d.cost),
                        borderColor: '#ea580c',
                        backgroundColor: 'rgba(234, 88, 12, 0.1)',
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: { responsive: true, maintainAspectRatio: true }
            });
            
            document.getElementById('serviceList').innerHTML = billing.services.map(s => `
                <div style="display:flex; justify-content:space-between; font-size:11px; padding:4px 0;">
                    <span>📦 ${s.name}</span>
                    <span style="color:#ea580c; font-weight:700;">$${s.cost.toLocaleString()}</span>
                </div>
            `).join('');
        }
        
        function addTicketToList(ticket) {
            const container = document.getElementById('recentTickets');
            if (container.children.length === 0 || container.innerHTML.includes('No tickets')) container.innerHTML = '';
            const severityColor = ticket.severity === 'CRITICAL' ? '#dc2626' : ticket.severity === 'HIGH' ? '#f97316' : '#f59e0b';
            const div = document.createElement('div');
            div.className = 'ticket-item';
            div.style.borderLeftColor = severityColor;
            div.innerHTML = `
                <div style="display:flex; justify-content:space-between;">
                    <strong style="color:#ea580c;">#${ticket.id}</strong>
                    <span style="color:${severityColor};">${ticket.severity}</span>
                </div>
                <div style="font-size:12px;">${escapeHtml(ticket.title)}</div>
                <div style="font-size:10px; color:#78716c;">${ticket.cloud_region || 'us-east-1'}</div>
            `;
            container.prepend(div);
            if (container.children.length > 5) container.removeChild(container.lastChild);
        }
        
        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const msg = input.value.trim();
            if (!msg) return;
            
            const chatDiv = document.getElementById('chatMessages');
            chatDiv.innerHTML += `<div class="message user-message">${escapeHtml(msg)}</div>`;
            input.value = '';
            chatDiv.scrollTop = chatDiv.scrollHeight;
            
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg })
                });
                const data = await res.json();
                chatDiv.innerHTML += `<div class="message bot-message">${escapeHtml(data.reply).replace(/\\\\n/g, '<br>')}</div>`;
                chatDiv.scrollTop = chatDiv.scrollHeight;
            } catch (err) {
                chatDiv.innerHTML += `<div class="message bot-message">❌ Error: ${err.message}</div>`;
            }
        }
        
        function quickCreateTicket(pod, message, severity) {
            document.getElementById('ticketTitle').value = `Issue on ${pod}`;
            document.getElementById('ticketDesc').value = message;
            const severitySelect = document.getElementById('ticketSeverity');
            if (severity === 'CRITICAL') severitySelect.value = 'CRITICAL';
            else if (severity === 'ERROR') severitySelect.value = 'HIGH';
            else if (severity === 'WARNING') severitySelect.value = 'MEDIUM';
            severitySelect.scrollIntoView({ behavior: 'smooth' });
            showAlert('📝 Quick ticket form populated!', 'info');
        }
        
        async function createTicket() {
            const title = document.getElementById('ticketTitle').value;
            const severity = document.getElementById('ticketSeverity').value;
            const desc = document.getElementById('ticketDesc').value;
            
            if (!title || !desc) {
                showAlert('⚠️ Please fill in both title and description');
                return;
            }
            
            try {
                const res = await fetch('/api/tickets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, severity, description: desc, created_by: 'User' })
                });
                const data = await res.json();
                if (data.success) {
                    showAlert(`✅ Ticket #${data.ticket.id} created! Email sent.`);
                    document.getElementById('ticketTitle').value = '';
                    document.getElementById('ticketDesc').value = '';
                    addTicketToList(data.ticket);
                }
            } catch (err) {
                showAlert('❌ Error creating ticket: ' + err.message);
            }
        }
        
        async function exportLogs() {
            try {
                const res = await fetch('/api/logs/export');
                const data = await res.json();
                const blob = new Blob([JSON.stringify(data.logs, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `logs_${new Date().toISOString()}.json`;
                a.click();
                URL.revokeObjectURL(url);
                showAlert('📎 Logs exported successfully!');
            } catch (err) {
                showAlert('❌ Export failed: ' + err.message);
            }
        }
        
        function setFilter(f) {
            filter = f;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            renderLogs();
        }
        
        function stopStreaming() { streaming = false; }
        function startStreaming() { streaming = true; }
        
        function escapeHtml(str) {
            return str.replace(/[&<>]/g, function(m) {
                if (m === '&') return '&amp;';
                if (m === '<') return '&lt;';
                if (m === '>') return '&gt;';
                return m;
            });
        }
        
        loadPodInfo();
        initVoice();
        connect();
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)