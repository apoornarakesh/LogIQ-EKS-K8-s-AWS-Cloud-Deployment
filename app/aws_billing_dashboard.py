"""
AWS Billing Dashboard - Real AWS Cost Metrics with Charts
"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os

# AWS Billing Integration
try:
    import boto3
    from boto3.session import Session
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    print("⚠️  boto3 not installed. Install with: pip install boto3")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Cost Explorer Client
ce_client = None
billing_data_cache = []
last_fetch_time = None

def get_aws_cost_client():
    """Initialize AWS Cost Explorer client"""
    global ce_client
    
    if not AWS_AVAILABLE:
        return None
    
    try:
        # Try to get AWS credentials from environment or default profile
        session = boto3.Session()
        ce_client = session.client('ce', region_name='us-east-1')
        
        # Test the connection
        ce_client.get_cost_and_usage(
            TimePeriod={'Start': '2025-01-01', 'End': '2025-01-02'},
            Granularity='DAILY',
            Metrics=['BlendedCost']
        )
        print("✅ Connected to AWS Cost Explorer")
        return ce_client
    except Exception as e:
        print(f"❌ AWS Cost Explorer connection failed: {e}")
        print("\n📌 To fix, configure AWS credentials:")
        print("   1. AWS CLI: aws configure")
        print("   2. Or set environment variables:")
        print("      export AWS_ACCESS_KEY_ID=your_key")
        print("      export AWS_SECRET_ACCESS_KEY=your_secret")
        print("      export AWS_DEFAULT_REGION=us-east-1")
        return None

def fetch_aws_billing_data(days_back: int = 30):
    """Fetch real AWS billing data from Cost Explorer"""
    global ce_client, billing_data_cache, last_fetch_time
    
    if ce_client is None:
        ce_client = get_aws_cost_client()
    
    if ce_client is None:
        return generate_sample_billing_data()
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates as YYYY-MM-DD
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        print(f"📡 Fetching AWS billing data from {start_str} to {end_str}")
        
        # Get daily cost breakdown by service
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_str,
                'End': end_str
            },
            Granularity='DAILY',
            Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'}
            ]
        )
        
        # Process the response
        daily_costs = []
        service_totals = {}
        total_cost = 0.0
        
        for result in response['ResultsByTime']:
            date = result['TimePeriod']['Start']
            daily_total = 0.0
            
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                if cost > 0:
                    daily_total += cost
                    service_totals[service] = service_totals.get(service, 0) + cost
            
            daily_costs.append({
                'date': date,
                'cost': round(daily_total, 2)
            })
            total_cost += daily_total
        
        # Get monthly forecast
        forecast_response = ce_client.get_cost_forecast(
            TimePeriod={
                'Start': end_str,
                'End': (end_date + timedelta(days=30)).strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metric='BLENDED_COST'
        )
        
        forecast_cost = float(forecast_response['Total']['Amount']) if 'Total' in forecast_response else 0
        
        # Prepare service breakdown
        services = [{'name': s, 'cost': round(c, 2)} for s, c in sorted(service_totals.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        billing_data = {
            'total_cost': round(total_cost, 2),
            'forecast_cost': round(forecast_cost, 2),
            'daily_breakdown': daily_costs,
            'service_breakdown': services,
            'currency': 'USD',
            'period': {
                'start': start_str,
                'end': end_str
            },
            'last_updated': datetime.now().isoformat()
        }
        
        billing_data_cache = billing_data
        last_fetch_time = datetime.now()
        
        print(f"✅ Fetched billing data: Total ${round(total_cost, 2)}")
        return billing_data
        
    except Exception as e:
        print(f"❌ Error fetching AWS billing data: {e}")
        return generate_sample_billing_data()

def generate_sample_billing_data():
    """Generate sample billing data for demo when AWS not available"""
    print("📊 Using sample billing data (AWS credentials not configured)")
    
    days = 30
    daily_costs = []
    total = 0
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i-1)).strftime('%Y-%m-%d')
        cost = round(50 + (i % 7) * 5 + (i % 3) * 3, 2)
        total += cost
        daily_costs.append({'date': date, 'cost': cost})
    
    services = [
        {'name': 'Amazon EC2', 'cost': round(total * 0.35, 2)},
        {'name': 'Amazon S3', 'cost': round(total * 0.15, 2)},
        {'name': 'AWS Lambda', 'cost': round(total * 0.12, 2)},
        {'name': 'Amazon RDS', 'cost': round(total * 0.10, 2)},
        {'name': 'Amazon EKS', 'cost': round(total * 0.08, 2)},
        {'name': 'AWS Data Transfer', 'cost': round(total * 0.07, 2)},
        {'name': 'Amazon CloudWatch', 'cost': round(total * 0.05, 2)},
        {'name': 'AWS KMS', 'cost': round(total * 0.03, 2)},
        {'name': 'AWS WAF', 'cost': round(total * 0.03, 2)},
        {'name': 'Other Services', 'cost': round(total * 0.02, 2)}
    ]
    
    return {
        'total_cost': round(total, 2),
        'forecast_cost': round(total * 1.1, 2),
        'daily_breakdown': daily_costs,
        'service_breakdown': services,
        'currency': 'USD',
        'period': {
            'start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'end': datetime.now().strftime('%Y-%m-%d')
        },
        'last_updated': datetime.now().isoformat(),
        'is_sample': True
    }

# WebSocket for real-time updates
connected_clients = []

async def billing_data_broadcaster():
    """Broadcast billing data to all connected clients every 30 seconds"""
    while True:
        if connected_clients:
            billing_data = fetch_aws_billing_data(days_back=30)
            for client in connected_clients[:]:
                try:
                    await client.send_text(json.dumps({
                        'type': 'billing_update',
                        'data': billing_data
                    }))
                except:
                    if client in connected_clients:
                        connected_clients.remove(client)
        await asyncio.sleep(30)  # Update every 30 seconds

@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 60)
    print("💰 AWS Billing Dashboard Started")
    print("=" * 60)
    print("\n📊 Dashboard URL: http://localhost:8000")
    print("📡 Fetching real AWS billing data via Cost Explorer")
    print("\n" + "=" * 60 + "\n")
    
    asyncio.create_task(billing_data_broadcaster())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    
    # Send initial billing data
    billing_data = fetch_aws_billing_data(days_back=30)
    await websocket.send_text(json.dumps({
        'type': 'billing_update',
        'data': billing_data
    }))
    
    try:
        while True:
            await websocket.receive_text()
    except:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# Dashboard HTML with Charts
HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogIQ AWS Billing Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
            color: white;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .aws-badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-right: 10px;
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
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-label {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .stat-value {
            font-size: 42px;
            font-weight: bold;
            color: #ee5a24;
        }
        
        .stat-sub {
            color: #999;
            font-size: 12px;
            margin-top: 10px;
        }
        
        /* Charts Grid */
        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .chart-card {
            background: white;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .chart-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }
        
        canvas {
            max-height: 350px;
        }
        
        /* Service Table */
        .services-card {
            background: white;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .service-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .service-table th {
            text-align: left;
            padding: 12px;
            background: #f8f9fa;
            color: #333;
            font-weight: 600;
        }
        
        .service-table td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        
        .cost-bar {
            background: linear-gradient(90deg, #ff6b6b, #ee5a24);
            height: 6px;
            border-radius: 3px;
            margin-top: 5px;
            width: 0%;
            transition: width 0.5s ease;
        }
        
        .refresh-info {
            text-align: center;
            margin-top: 20px;
            color: #888;
            font-size: 12px;
        }
        
        .status-badge {
            display: inline-block;
            background: #10b981;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            margin-left: 10px;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .updating {
            animation: pulse 1s ease-in-out;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>💰 AWS Billing & Cost Dashboard</h1>
            <p>Real-time AWS cost metrics from Cost Explorer | Auto-updates every 30 seconds</p>
            <div style="margin-top: 15px;">
                <span class="aws-badge">☁️ AWS Cost Explorer</span>
                <span class="aws-badge" id="dataSource">📡 Live Data</span>
                <span class="aws-badge" id="lastUpdate">Updating...</span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Cost (Last 30 Days)</div>
                <div class="stat-value" id="totalCost">$0.00</div>
                <div class="stat-sub" id="costPeriod"></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Forecast (Next 30 Days)</div>
                <div class="stat-value" id="forecastCost">$0.00</div>
                <div class="stat-sub">Estimated based on current trends</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Daily Average</div>
                <div class="stat-value" id="dailyAvg">$0.00</div>
                <div class="stat-sub">Last 30 days average</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">📈 Daily Cost Trend</div>
                <canvas id="costTrendChart"></canvas>
            </div>
            <div class="chart-card">
                <div class="chart-title">🥧 Cost by Service</div>
                <canvas id="serviceChart"></canvas>
            </div>
        </div>
        
        <div class="services-card">
            <div class="chart-title">📋 Service Breakdown</div>
            <table class="service-table" id="serviceTable">
                <thead>
                    <tr><th>Service</th><th>Cost (USD)</th><th>% of Total</th></tr>
                </thead>
                <tbody id="serviceTableBody">
                    <tr><td colspan="3" style="text-align: center;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="refresh-info" id="refreshInfo">
            🔄 Data refreshes automatically every 30 seconds
        </div>
    </div>
    
    <script>
        let costTrendChart = null;
        let serviceChart = null;
        let ws = null;
        
        function initCharts() {
            const ctx1 = document.getElementById('costTrendChart').getContext('2d');
            costTrendChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Daily Cost (USD)',
                        data: [],
                        borderColor: '#ee5a24',
                        backgroundColor: 'rgba(238, 90, 36, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointBackgroundColor: '#ee5a24'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: { callbacks: { label: (ctx) => `$${ctx.raw.toFixed(2)}` } }
                    },
                    scales: { y: { ticks: { callback: (v) => '$' + v } } }
                }
            });
            
            const ctx2 = document.getElementById('serviceChart').getContext('2d');
            serviceChart = new Chart(ctx2, {
                type: 'doughnut',
                data: { labels: [], datasets: [{ data: [], backgroundColor: [] }] },
                options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'right' } } }
            });
        }
        
        function getRandomColor(index) {
            const colors = ['#ff6b6b', '#ee5a24', '#feca57', '#48dbfb', '#ff9ff3', '#54a0ff', '#5f27cd', '#00d2d3', '#1dd1a1', '#f368e0'];
            return colors[index % colors.length];
        }
        
        function updateDashboard(billingData) {
            const total = billingData.total_cost || 0;
            const forecast = billingData.forecast_cost || 0;
            const dailyData = billingData.daily_breakdown || [];
            const services = billingData.service_breakdown || [];
            
            document.getElementById('totalCost').innerHTML = `$${total.toFixed(2)}`;
            document.getElementById('forecastCost').innerHTML = `$${forecast.toFixed(2)}`;
            
            const dailyAvg = dailyData.length > 0 ? total / dailyData.length : 0;
            document.getElementById('dailyAvg').innerHTML = `$${dailyAvg.toFixed(2)}`;
            
            if (billingData.period) {
                document.getElementById('costPeriod').innerHTML = `${billingData.period.start} to ${billingData.period.end}`;
            }
            
            if (billingData.last_updated) {
                const updateTime = new Date(billingData.last_updated).toLocaleTimeString();
                document.getElementById('lastUpdate').innerHTML = `🕐 Last: ${updateTime}`;
            }
            
            if (billingData.is_sample) {
                document.getElementById('dataSource').innerHTML = '📊 Sample Data (Demo Mode)';
                document.getElementById('dataSource').style.background = '#f59e0b';
            } else {
                document.getElementById('dataSource').innerHTML = '✅ Live AWS Data';
                document.getElementById('dataSource').style.background = '#10b981';
            }
            
            // Update trend chart
            const labels = dailyData.map(d => d.date.substring(5));
            const costs = dailyData.map(d => d.cost);
            costTrendChart.data.labels = labels;
            costTrendChart.data.datasets[0].data = costs;
            costTrendChart.update();
            
            // Update service chart
            const serviceNames = services.map(s => s.name);
            const serviceCosts = services.map(s => s.cost);
            serviceChart.data.labels = serviceNames;
            serviceChart.data.datasets[0].data = serviceCosts;
            serviceChart.data.datasets[0].backgroundColor = serviceNames.map((_, i) => getRandomColor(i));
            serviceChart.update();
            
            // Update service table
            const totalCost = services.reduce((sum, s) => sum + s.cost, 0);
            const tbody = document.getElementById('serviceTableBody');
            tbody.innerHTML = services.map(s => {
                const percent = totalCost > 0 ? ((s.cost / totalCost) * 100).toFixed(1) : 0;
                return `
                    <tr>
                        <td><strong>${s.name}</strong></td>
                        <td>$${s.cost.toFixed(2)}</td>
                        <td>
                            ${percent}%
                            <div class="cost-bar" style="width: ${percent}%;"></div>
                        </td>
                    </tr>
                `;
            }).join('');
            
            // Add animation
            document.querySelector('.refresh-info').classList.add('updating');
            setTimeout(() => document.querySelector('.refresh-info').classList.remove('updating'), 500);
        }
        
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/ws');
            ws.onopen = () => console.log('✅ WebSocket connected');
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'billing_update') {
                    updateDashboard(data.data);
                }
            };
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }
        
        initCharts();
        connectWebSocket();
    </script>
</body>
</html>
'''

@app.get("/")
@app.get("/dashboard")
async def dashboard():
    return HTMLResponse(HTML)

@app.get("/api/billing")
async def get_billing_api():
    """REST API endpoint for billing data"""
    return fetch_aws_billing_data(days_back=30)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
