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
st.set_page_config(page_title="Smart Parking System", layout="wide", initial_sidebar_state="expanded")

# ---------------- CUSTOM CSS FOR ATTRACTIVE UI ----------------
st.markdown("""
<style>
    /* Main background and text */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff;
    }
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
    }
    /* Cards for slots */
    .slot-card {
        background: rgba(255,255,255,0.2);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255,255,255,0.18);
        transition: transform 0.2s;
    }
    .slot-card:hover {
        transform: scale(1.02);
    }
    .slot-free {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        color: #000;
    }
    .slot-occupied {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: #fff;
    }
    /* Metric boxes */
    .metric-box {
        background: rgba(255,255,255,0.25);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    /* Buttons */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 10px 30px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(45deg, #764ba2, #667eea);
        transform: scale(1.05);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    /* Success/info/warning boxes */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.1);
        border-radius: 50px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 50px;
        color: white;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255,255,255,0.3);
    }
    /* Headers */
    h1, h2, h3 {
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    /* Dataframes */
    .dataframe {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- FILE PATHS ----------------
PARKING_CSV = "parking_data.csv"
BILLING_CSV = "billing_data.csv"
INVOICE_DIR = "invoices"
os.makedirs(INVOICE_DIR, exist_ok=True)

# ---------------- CONSTANT ----------------
RATE_PER_HOUR = 20
UPI_ID = "smartparking@upi"

# ---------------- LOGIN ----------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Smart Parking Admin Login")
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Username", placeholder="Enter username")
            p = st.text_input("Password", type="password", placeholder="Enter password")
            if st.button("Login", use_container_width=True):
                if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    st.stop()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/null/parking.png", width=80)
    st.markdown("## Smart Parking")
    st.markdown("---")
    st.markdown(f"**Welcome, Admin** 👋")
    st.markdown(f"**Rate:** ₹{RATE_PER_HOUR}/hour")
    st.markdown(f"**UPI ID:** `{UPI_ID}`")
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ---------------- INIT CSV ----------------
if not os.path.exists(PARKING_CSV):
    with open(PARKING_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["Slot", "Status", "Vehicle", "EntryTime"])

if not os.path.exists(BILLING_CSV):
    with open(BILLING_CSV, "w", newline="") as f:
        csv.writer(f).writerow(
            ["Vehicle", "Slot", "EntryTime", "ExitTime", "Minutes", "Amount", "PaymentStatus"]
        )

# ---------------- SESSION STATE ----------------
if "slots" not in st.session_state:
    st.session_state.slots = {
        i: {"status": "Free", "vehicle": None, "entry_time": None}
        for i in range(1, 6)
    }

if "payment_pending" not in st.session_state:
    st.session_state.payment_pending = None

# ---------------- MAIN TABS ----------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🚗 Parking Operations", "💳 Billing & Payment", "📈 Revenue Analytics"])

# ==================== TAB 1: DASHBOARD ====================
with tab1:
    st.header("📊 Live Dashboard")

    # Metrics
    total = len(st.session_state.slots)
    free = sum(1 for s in st.session_state.slots.values() if s["status"] == "Free")
    occupied = total - free

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-box"><h3>🅿 Total Slots</h3><h2>{}</h2></div>'.format(total), unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-box"><h3>🟢 Free</h3><h2>{}</h2></div>'.format(free), unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-box"><h3>🔴 Occupied</h3><h2>{}</h2></div>'.format(occupied), unsafe_allow_html=True)
    with col4:
        # Today's revenue quick peek
        if os.path.exists(BILLING_CSV):
            df_quick = pd.read_csv(BILLING_CSV)
            if not df_quick.empty:
                df_quick["ExitTime"] = pd.to_datetime(df_quick["ExitTime"], errors="coerce")
                today_rev = df_quick[df_quick["ExitTime"].dt.date == datetime.now().date()]["Amount"].sum()
                st.markdown(f'<div class="metric-box"><h3>💰 Today</h3><h2>₹{today_rev}</h2></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="metric-box"><h3>💰 Today</h3><h2>₹0</h2></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-box"><h3>💰 Today</h3><h2>₹0</h2></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Live Slot Status with visual cards
    st.subheader("🅿️ Slot Status")
    cols = st.columns(5)
    for i, (slot, data) in enumerate(st.session_state.slots.items()):
        with cols[i]:
            if data["status"] == "Free":
                st.markdown(f'''
                <div class="slot-card slot-free">
                    <h3>Slot {slot}</h3>
                    <p style="font-size: 24px;">🟢</p>
                    <p>Free</p>
                </div>
                ''', unsafe_allow_html=True)
            else:
                mins = int((datetime.now() - data["entry_time"]).total_seconds() / 60)
                st.markdown(f'''
                <div class="slot-card slot-occupied">
                    <h3>Slot {slot}</h3>
                    <p style="font-size: 24px;">🔴</p>
                    <p><b>{data["vehicle"]}</b></p>
                    <p>{mins} min</p>
                </div>
                ''', unsafe_allow_html=True)

# ==================== TAB 2: PARKING OPERATIONS ====================
with tab2:
    st.header("🚗 Parking Operations")

    col1, col2 = st.columns(2)

    # ----- MANUAL ENTRY -----
    with col1:
        st.subheader("📝 Manual Entry")
        vehicle = st.text_input("Vehicle Number", key="manual_vehicle")
        free_slots = [s for s in st.session_state.slots if st.session_state.slots[s]["status"] == "Free"]
        if free_slots:
            slot = st.selectbox("Select Slot", free_slots, key="manual_slot")
            if st.button("🅿 Park Vehicle", use_container_width=True):
                now = datetime.now()
                st.session_state.slots[slot] = {
                    "status": "Occupied",
                    "vehicle": vehicle,
                    "entry_time": now
                }
                with open(PARKING_CSV, "a", newline="") as f:
                    csv.writer(f).writerow([slot, "Occupied", vehicle, now.isoformat()])
                st.success(f"✅ Vehicle {vehicle} parked in Slot {slot}")
                st.rerun()
        else:
            st.warning("⚠️ Parking Full")

    # ----- ANPR SIMULATION -----
    with col2:
        st.subheader("📷 ANPR Simulation")
        if st.button("📸 Scan Number Plate", use_container_width=True):
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
                st.success(f"📡 Detected: {plate} → Slot {slot}")
                st.rerun()
            else:
                st.error("❌ Parking Full")

    st.markdown("---")
    # Optionally show recent entries from CSV
    if os.path.exists(PARKING_CSV):
        df_park = pd.read_csv(PARKING_CSV)
        if not df_park.empty:
            st.subheader("📋 Recent Parking Records")
            st.dataframe(df_park.tail(5), use_container_width=True)

# ==================== TAB 3: BILLING & PAYMENT ====================
with tab3:
    st.header("💳 Billing & Payment")

    # Exit section
    st.subheader("🚙 Vehicle Exit")
    exit_slot = st.selectbox("Select Slot to Exit", st.session_state.slots.keys(), key="exit_slot")
    if st.button("💰 Calculate Bill", use_container_width=True):
        data = st.session_state.slots[exit_slot]
        if data["status"] == "Occupied":
            exit_time = datetime.now()
            entry_time = data["entry_time"]
            minutes = int((exit_time - entry_time).total_seconds() / 60)
            hours = max(1, minutes // 60)
            amount = hours * RATE_PER_HOUR

            st.session_state.payment_pending = {
                "vehicle": data["vehicle"],
                "slot": exit_slot,
                "entry": entry_time,
                "exit": exit_time,
                "minutes": minutes,
                "amount": amount
            }

            # Free the slot immediately
            st.session_state.slots[exit_slot] = {
                "status": "Free",
                "vehicle": None,
                "entry_time": None
            }
            st.rerun()
        else:
            st.warning("⚠️ Slot already free")

    st.markdown("---")

    # Payment Gateway
    if st.session_state.payment_pending:
        bill = st.session_state.payment_pending
        st.subheader("💳 UPI Payment Gateway")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'''
            <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 15px;">
                <h3 style="color:white;">Bill Details</h3>
                <p>🚗 Vehicle: <b>{bill["vehicle"]}</b></p>
                <p>🅿 Slot: <b>{bill["slot"]}</b></p>
                <p>⏱ Duration: <b>{bill["minutes"]} minutes</b></p>
                <p>💰 Amount: <b>₹{bill["amount"]}</b></p>
                <p>📅 Entry: {bill["entry"].strftime("%Y-%m-%d %H:%M")}</p>
                <p>📅 Exit: {bill["exit"].strftime("%Y-%m-%d %H:%M")}</p>
            </div>
            ''', unsafe_allow_html=True)
        with col2:
            st.markdown(f'''
            <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 15px; text-align: center;">
                <h3 style="color:white;">Scan & Pay</h3>
                <p>UPI ID: <code>{UPI_ID}</code></p>
            ''', unsafe_allow_html=True)
            qr_data = f"upi://pay?pa={UPI_ID}&pn=SmartParking&am={bill['amount']}&cu=INR"
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_data}", width=200)
            st.markdown('</div>', unsafe_allow_html=True)

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ I Have Paid", use_container_width=True):
                # Save to billing CSV
                with open(BILLING_CSV, "a", newline="") as f:
                    csv.writer(f).writerow([
                        bill["vehicle"],
                        bill["slot"],
                        bill["entry"].isoformat(),
                        bill["exit"].isoformat(),
                        bill["minutes"],
                        bill["amount"],
                        "PAID"
                    ])

                # Generate PDF invoice
                filename = f"{INVOICE_DIR}/invoice_{bill['vehicle']}_{bill['exit'].strftime('%Y%m%d_%H%M%S')}.pdf"
                c = canvas.Canvas(filename, pagesize=A4)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(100, 800, "Smart Parking Invoice")
                c.setFont("Helvetica", 12)
                c.drawString(100, 770, f"Vehicle: {bill['vehicle']}")
                c.drawString(100, 750, f"Slot: {bill['slot']}")
                c.drawString(100, 730, f"Entry Time: {bill['entry'].strftime('%Y-%m-%d %H:%M')}")
                c.drawString(100, 710, f"Exit Time: {bill['exit'].strftime('%Y-%m-%d %H:%M')}")
                c.drawString(100, 690, f"Duration: {bill['minutes']} minutes")
                c.drawString(100, 670, f"Amount Paid: ₹{bill['amount']}")
                c.drawString(100, 650, f"UPI ID: {UPI_ID}")
                c.save()

                with open(filename, "rb") as f:
                    st.download_button("📄 Download Invoice", f, file_name=os.path.basename(filename), use_container_width=True)

                st.success("🎉 Payment Successful! Thank you.")
                st.session_state.payment_pending = None
                st.rerun()
        with colB:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.payment_pending = None
                st.rerun()
    else:
        st.info("👆 No pending payment. Process an exit to continue.")

# ==================== TAB 4: REVENUE ANALYTICS ====================
with tab4:
    st.header("📈 Revenue Analytics")

    if os.path.exists(BILLING_CSV):
        df = pd.read_csv(BILLING_CSV)
        if not df.empty:
            df["ExitTime"] = pd.to_datetime(df["ExitTime"], errors="coerce")
            df["EntryTime"] = pd.to_datetime(df["EntryTime"], errors="coerce")

            # Daily revenue
            today = datetime.now().date()
            daily = df[df["ExitTime"].dt.date == today]["Amount"].sum()
            st.metric("Today's Revenue", f"₹{daily}")

            # Monthly revenue chart
            df["Month"] = df["ExitTime"].dt.to_period("M").astype(str)
            monthly = df.groupby("Month")["Amount"].sum().reset_index()
            monthly.columns = ["Month", "Revenue"]

            st.subheader("Monthly Revenue Trend")
            st.line_chart(monthly.set_index("Month"))

            # Optional: Show recent transactions
            with st.expander("📋 Recent Transactions"):
                st.dataframe(df[["Vehicle", "Slot", "ExitTime", "Amount"]].tail(10), use_container_width=True)
        else:
            st.info("No revenue data yet. Complete some payments to see analytics.")
    else:
        st.info("No billing records found.")
