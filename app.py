import streamlit as st
from ping3 import ping
import pandas as pd
import plotly.express as px
import subprocess
import platform
import re
import sqlite3
import time
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Wi-Fi & ISP Performance Engine", layout="wide")

st.title("🌐 Real-Time Wi-Fi & ISP Performance Engine")
st.write("Full-featured Network Telemetry & Historical Analytics Platform")

# 2. Database Initialization
def init_db():
    conn = sqlite3.connect("network_data.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        latency_ms REAL,
        signal_pct INTEGER,
        rssi_dbm INTEGER,
        health_score INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_db()

# 3. Helper Functions
def get_wifi_rssi():
    os_type = platform.system()
    try:
        if os_type == "Windows":
            cmd = subprocess.check_output("netsh wlan show interfaces", shell=True).decode("utf-8")
            match = re.search(r"Signal\s*:\s*(\d+)%", cmd)
            if match:
                percent = int(match.group(1))
                rssi = int((percent / 2) - 100)
                return rssi, percent
    except Exception:
        pass
    return -60, 80

def check_network():
    response = ping("8.8.8.8", timeout=2)
    rssi, signal_pct = get_wifi_rssi()
    now = datetime.now().strftime("%H:%M:%S")

    if response is None:
        return None, "Offline ❌", rssi, signal_pct, now, 0
    else:
        latency = round(response * 1000, 2)
        # Health Score Calculation (0 to 100)
        health = max(0, min(100, int(100 - (latency / 4) + (signal_pct / 2))))
        
        if latency < 50:
            status = "Excellent 🚀"
        elif latency < 150:
            status = "Normal 🟡"
        else:
            status = "Slow Network 🔴"
            
        return latency, status, rssi, signal_pct, now, health

# Fetch Live Metrics
latency, status, rssi, signal_pct, timestamp, health = check_network()

# Save to Database
if latency is not None:
    conn = sqlite3.connect("network_data.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO metrics (timestamp, latency_ms, signal_pct, rssi_dbm, health_score) VALUES (?, ?, ?, ?, ?)",
        (timestamp, latency, signal_pct, rssi, health)
    )
    conn.commit()
    conn.close()

# 4. Display Real-Time Metrics
col1, col2, col3, col4 = st.columns(4)

if latency is not None:
    col1.metric("⚡ Latency (Ping)", f"{latency} ms")
    col2.metric("📶 Wi-Fi Signal", f"{signal_pct}% ({rssi} dBm)")
    col3.metric("🛡️ Health Score", f"{health} / 100")
    col4.metric("📊 Network Status", status)
else:
    col1.metric("Status", "NO INTERNET CONNECTION")

st.markdown("---")

# 5. Fetch Historical Data from DB for Graphs
conn = sqlite3.connect("network_data.db")
df = pd.read_sql_query("SELECT * FROM metrics ORDER BY id DESC LIMIT 40", conn)
conn.close()

if not df.empty:
    df = df.iloc[::-1] # Reverse for left-to-right timeline
    
    st.subheader("📈 Real-Time Analytics Dashboard")
    
    tab1, tab2 = st.tabs(["Latency Fluctuation", "Network Health History"])
    
    with tab1:
        fig_latency = px.line(df, x="timestamp", y="latency_ms", title="Latency (ms) over Time", markers=True)
        st.plotly_chart(fig_latency, use_container_width=True)
        
    with tab2:
        fig_health = px.area(df, x="timestamp", y="health_score", title="Overall Health Score (%) History")
        st.plotly_chart(fig_health, use_container_width=True)

    with st.expander("📋 Stored Database Logs (SQLite)"):
        st.dataframe(df, use_container_width=True)

# 6. Auto-Refresh Engine (Runs continuously every 3 seconds)
time.sleep(3)
st.rerun()