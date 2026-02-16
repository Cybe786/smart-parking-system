import streamlit as st
from datetime import datetime
import random
import csv
import os
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import time

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Smart Parking System", layout="wide", initial_sidebar_state="collapsed")

# ---------------- CUSTOM CSS FOR ATTRACTIVE UI ----------------
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 1rem 2rem;
    }
    /* Title */
    .title {
        text-align: center;
        font-size: 3rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    .metric-label {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin-top: 0.5rem;
    }
    /* Slot cards */
    .slot-card {
        border-radius: 15px;
        padding: 1rem;
        text-align: center;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }
    .slot-card:hover {
        transform: scale(1.05);
    }
    .slot-free {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        color: #1e3c72;
    }
    .slot-occupied {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    /* Buttons */
    .stButton > button {
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    /* Section headers */
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 3px solid #3498db;
        padding-bottom: 0.5rem;
    }
    /* Login container */
    .login-box {
        max-width: 400px;
        margin: 5rem auto;
        padding: 2rem;
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ---------------- FILE PATHS ----------------
PARKING_CSV = "parking_data.csv"
BILLING_CSV = "billing_data.csv"
INVOICE_DIR = "invoices"

os.makedirs(INVOICE_DIR, exist_ok=True)

# ---------------- LOGIN ----------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🔐 Smart Parking Admin</h1>", unsafe_allow_html=True)
    u = st.text_input("Username", placeholder="Enter username")
    p = st.text_input("Password", type="password", placeholder="Enter password")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("Login", use_container_width=True):
            if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid Credentials")
    st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    login()
    st.stop()

# Logout button in sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/null/parking.png", width=80)
    st.markdown("## **Smart Parking**")
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ---------------- CONSTANT ----------------
RATE_PER_HOUR = 20

# ---------------- INIT FILES ----------------
if not os.path.exists(PARKING_CSV):
    with open(PARKING_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["Slot", "Status", "Vehicle", "EntryTime"])

if not os.path.exists(BILLING_CSV):
    with open(BILLING_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["Vehicle", "Slot", "EntryTime", "ExitTime", "Minutes", "Amount"])

# ---------------- SESSION STATE ----------------
if "slots" not in st.session_state:
    st.session_state.slots = {
        i: {"status": "Free", "vehicle": None, "entry_time": None}
        for i in range(1, 6)
    }

# ---------------- MAIN UI ----------------
st.markdown("<h1 class='title'>🅿 Smart Parking Management</h1>", unsafe_allow_html=True)

# ---------------- DASHBOARD METRICS ----------------
total = len(st.session_state.slots)
free = sum(1 for s in st.session_state.slots.values() if s["status"] == "Free")
occupied = total - free

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Total Slots</div>
        <div class='metric-value'>{total}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class='metric-card' style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);'>
        <div class='metric-label'>Free Slots</div>
        <div class='metric-value'>{free}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class='metric-card' style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);'>
        <div class='metric-label'>Occupied Slots</div>
        <div class='metric-value'>{occupied}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ---------------- LIVE SLOT STATUS ----------------
st.markdown("<div class='section-header'>📊 Live Slot Status</div>", unsafe_allow_html=True)
cols = st.columns(5)
for i, (slot, data) in enumerate(st.session_state.slots.items()):
    if data["status"] == "Free":
        cols[i].markdown(f"""
        <div class='slot-card slot-free'>
            <div style='font-size: 1.5rem;'>🅿️{slot}</div>
            <div style='font-size: 1rem;'>🟢 FREE</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        mins = int((datetime.now() - data["entry_time"]).total_seconds() / 60)
        cols[i].markdown(f"""
        <div class='slot-card slot-occupied'>
            <div style='font-size: 1.5rem;'>🅿️{slot}</div>
            <div style='font-size: 0.9rem;'>🔴 {data['vehicle']}</div>
            <div style='font-size: 0.8rem;'>{mins} min</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ---------------- TWO-COLUMN LAYOUT FOR ACTIONS ----------------
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("<div class='section-header'>🚗 Manual Entry</div>", unsafe_allow_html=True)
    vehicle = st.text_input("Vehicle Number", placeholder="e.g., MH12AB1234")
    free_slots = [s for s in st.session_state.slots if st.session_state.slots[s]["status"] == "Free"]
    if free_slots:
        slot = st.selectbox("Select Slot", free_slots)
        if st.button("Park Vehicle", use_container_width=True):
            now = datetime.now()
            st.session_state.slots[slot] = {
                "status": "Occupied",
                "vehicle": vehicle,
                "entry_time": now
            }
            with open(PARKING_CSV, "a", newline="") as f:
                csv.writer(f).writerow([slot, "Occupied", vehicle, now.isoformat()])
            st.success(f"✅ Vehicle {vehicle} parked in Slot {slot}")
            time.sleep(1)
            st.rerun()
    else:
        st.warning("⚠️ Parking Full")

with col_right:
    st.markdown("<div class='section-header'>📷 ANPR Entry</div>", unsafe_allow_html=True)
    st.markdown("Click to simulate camera capture")
    if st.button("Scan Number Plate", use_container_width=True):
        plate = f"MH{random.randint(10,99)}AB{random.randint(1000,9999)}"
        free_slots_anpr = [s for s in st.session_state.slots if st.session_state.slots[s]["status"] == "Free"]
        if free_slots_anpr:
            slot = free_slots_anpr[0]
            now = datetime.now()
            st.session_state.slots[slot] = {
                "status": "Occupied",
                "vehicle": plate,
                "entry_time": now
            }
            with open(PARKING_CSV, "a", newline="") as f:
                csv.writer(f).writerow([slot, "Occupied", plate, now.isoformat()])
            st.success(f"✅ Detected: {plate}")
            st.success(f"✅ Auto-parked in Slot {slot}")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Parking Full")

st.markdown("---")

# ---------------- EXIT SECTION ----------------
st.markdown("<div class='section-header'>🚙 Exit & Billing</div>", unsafe_allow_html=True)
col_exit1, col_exit2 = st.columns([1,1])
with col_exit1:
    exit_slot = st.selectbox("Select Slot to Exit", st.session_state.slots.keys())
with col_exit2:
    st.markdown("<br>", unsafe_allow_html=True)  # spacing
    if st.button("Process Exit", use_container_width=True):
        data = st.session_state.slots[exit_slot]
        if data["status"] == "Occupied":
            exit_time = datetime.now()
            entry_time = data["entry_time"]
            minutes = int((exit_time - entry_time).total_seconds() / 60)
            hours = max(1, minutes // 60)
            amount = hours * RATE_PER_HOUR

            # Save to billing
            with open(BILLING_CSV, "a", newline="") as f:
                csv.writer(f).writerow([
                    data["vehicle"],
                    exit_slot,
                    entry_time.isoformat(),
                    exit_time.isoformat(),
                    minutes,
                    amount
                ])

            # Generate invoice
            def generate_invoice(vehicle, slot, entry, exit_t, mins, amt):
                filename = f"{INVOICE_DIR}/invoice_{vehicle}_{exit_t.strftime('%Y%m%d_%H%M%S')}.pdf"
                c = canvas.Canvas(filename, pagesize=A4)
                width, height = A4
                c.setFont("Helvetica-Bold", 16)
                c.drawString(200, height - 50, "Parking Invoice")
                c.setFont("Helvetica", 12)
                c.drawString(50, height - 100, f"Vehicle: {vehicle}")
                c.drawString(50, height - 130, f"Slot: {slot}")
                c.drawString(50, height - 160, f"Entry Time: {entry}")
                c.drawString(50, height - 190, f"Exit Time: {exit_t}")
                c.drawString(50, height - 220, f"Duration: {mins} minutes")
                c.drawString(50, height - 250, f"Amount: ₹{amt}")
                c.save()
                return filename

            pdf = generate_invoice(data["vehicle"], exit_slot, entry_time, exit_time, minutes, amount)

            st.success(f"🚗 {data['vehicle']} | Duration: {minutes} min | Bill: ₹{amount}")
            with open(pdf, "rb") as f:
                st.download_button("📥 Download Invoice", f, file_name=os.path.basename(pdf))

            # Free slot
            st.session_state.slots[exit_slot] = {
                "status": "Free",
                "vehicle": None,
                "entry_time": None
            }
            time.sleep(1)
            st.rerun()
        else:
            st.warning("Slot already free")

st.markdown("---")

# ---------------- REVENUE ANALYTICS ----------------
st.markdown("<div class='section-header'>💰 Revenue Analytics</div>", unsafe_allow_html=True)
if os.path.exists(BILLING_CSV):
    df = pd.read_csv(BILLING_CSV)
    if not df.empty:
        df["ExitTime"] = pd.to_datetime(df["ExitTime"], errors="coerce")
        today = datetime.now().date()
        daily = df[df["ExitTime"].dt.date == today]["Amount"].sum()
        st.metric("Today's Revenue", f"₹{daily}")
        df["Month"] = df["ExitTime"].dt.to_period("M")
        monthly = df.groupby("Month")["Amount"].sum().astype(float)
        st.line_chart(monthly)
    else:
        st.info("No billing data yet")
else:
    st.info("No billing data yet")
