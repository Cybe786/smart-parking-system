import streamlit as st
from datetime import datetime
import csv
import os
import random
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ================= CONFIG =================
st.set_page_config(page_title="Smart Parking Admin", layout="wide")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"
RATE_PER_HOUR = 20
TOTAL_SLOTS = 5

PARKING_CSV = "parking_data.csv"
BILLING_CSV = "billing_data.csv"
INVOICE_DIR = "invoices"
os.makedirs(INVOICE_DIR, exist_ok=True)

# ================= MODERN GLASSMORPHISM CSS =================
st.markdown("""
<style>
body {
    background: linear-gradient(135deg,#0f172a,#020617);
}
.main {
    background: transparent;
}
.block-container {
    padding-top: 2rem;
}
h1, h2, h3 {
    color: #38bdf8;
}
.glass {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(15px);
    padding: 20px;
    border-radius: 15px;
    border: 1px solid rgba(255,255,255,0.1);
}
div.stButton > button {
    background: linear-gradient(90deg,#38bdf8,#0ea5e9);
    color: black;
    font-weight: bold;
    border-radius: 8px;
}
div.stButton > button:hover {
    background: linear-gradient(90deg,#0ea5e9,#38bdf8);
    color: white;
}
.stMetric {
    background: rgba(255,255,255,0.05);
    padding: 15px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# ================= CSV INIT =================
if not os.path.exists(PARKING_CSV):
    with open(PARKING_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["Slot","Status","Vehicle","EntryTime"])

if not os.path.exists(BILLING_CSV):
    with open(BILLING_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["Vehicle","Slot","EntryTime","ExitTime","Minutes","Amount"])

# ================= SESSION =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "slots" not in st.session_state:
    st.session_state.slots = {
        i: {"status":"Free","vehicle":None,"entry_time":None}
        for i in range(1,TOTAL_SLOTS+1)
    }

# ================= LOGIN =================
def login():
    st.markdown("<h1 style='text-align:center;'>🚀 Smart Parking Admin Panel</h1>",unsafe_allow_html=True)
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")

def logout():
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

if not st.session_state.logged_in:
    login()
    st.stop()

# ================= SIDEBAR =================
st.sidebar.title("📊 Admin Navigation")
page = st.sidebar.radio("Go to",
    ["Dashboard","Vehicle Entry","ANPR","Billing","Revenue"]
)
logout()

# ================= DASHBOARD =================
if page == "Dashboard":
    st.markdown("## 📈 System Overview")

    total = TOTAL_SLOTS
    free = sum(1 for s in st.session_state.slots.values() if s["status"]=="Free")
    occupied = total - free

    c1,c2,c3 = st.columns(3)
    c1.metric("🚘 Total Slots", total)
    c2.metric("🟢 Free Slots", free)
    c3.metric("🔴 Occupied Slots", occupied)

    st.markdown("### ⏱ Live Parking Status")
    cols = st.columns(TOTAL_SLOTS)
    for i,(slot,d) in enumerate(st.session_state.slots.items()):
        if d["status"]=="Free":
            cols[i].success(f"Slot {slot}\nFree")
        else:
            mins=int((datetime.now()-d["entry_time"]).total_seconds()/60)
            cols[i].error(f"Slot {slot}\n{mins} min")

# ================= VEHICLE ENTRY =================
if page == "Vehicle Entry":
    st.markdown("## 🚗 Manual Parking Entry")
    vehicle = st.text_input("Vehicle Number")
    free_slots = [s for s in st.session_state.slots if st.session_state.slots[s]["status"]=="Free"]

    if free_slots:
        slot = st.selectbox("Select Slot", free_slots)
        if st.button("Park Vehicle"):
            now = datetime.now()
            st.session_state.slots[slot] = {
                "status":"Occupied",
                "vehicle":vehicle,
                "entry_time":now
            }
            with open(PARKING_CSV,"a",newline="") as f:
                csv.writer(f).writerow([slot,"Occupied",vehicle,now.isoformat()])
            st.success("Vehicle Parked Successfully")
    else:
        st.warning("Parking Full")

# ================= ANPR =================
if page == "ANPR":
    st.markdown("## 📷 ANPR Simulation")
    if st.button("Scan Number Plate"):
        fake=f"MH{random.randint(10,99)}AB{random.randint(1000,9999)}"
        free_slots=[s for s in st.session_state.slots if st.session_state.slots[s]["status"]=="Free"]
        if free_slots:
            slot=free_slots[0]
            now=datetime.now()
            st.session_state.slots[slot]={
                "status":"Occupied",
                "vehicle":fake,
                "entry_time":now
            }
            st.success(f"Detected: {fake}")
            st.success(f"Auto Parked in Slot {slot}")
        else:
            st.error("Parking Full")

# ================= BILLING =================
if page == "Billing":
    st.markdown("## 💰 Billing System + Invoice")
    exit_slot=st.selectbox("Select Slot",st.session_state.slots.keys())

    if st.button("Generate Bill"):
        data=st.session_state.slots[exit_slot]
        if data["status"]=="Occupied":
            exit_time=datetime.now()
            entry=data["entry_time"]
            minutes=int((exit_time-entry).total_seconds()/60)
            hours=max(1,minutes//60)
            amount=hours*RATE_PER_HOUR

            with open(BILLING_CSV,"a",newline="") as f:
                csv.writer(f).writerow([
                    data["vehicle"],exit_slot,
                    entry.isoformat(),exit_time.isoformat(),
                    minutes,amount
                ])

            file=f"{INVOICE_DIR}/invoice_{data['vehicle']}.pdf"
            c=canvas.Canvas(file,pagesize=A4)
            c.drawString(200,800,"Parking Invoice")
            c.drawString(50,750,f"Vehicle: {data['vehicle']}")
            c.drawString(50,720,f"Minutes: {minutes}")
            c.drawString(50,690,f"Amount: ₹{amount}")
            c.save()

            st.success(f"Total Bill: ₹{amount}")

            with open(file,"rb") as f:
                st.download_button("Download Invoice",f,file_name=os.path.basename(file))

            st.session_state.slots[exit_slot]={"status":"Free","vehicle":None,"entry_time":None}
        else:
            st.warning("Slot already free")

# ================= REVENUE =================
if page == "Revenue":
    st.markdown("## 📊 Revenue Analytics")
    df=pd.read_csv(BILLING_CSV)

    if not df.empty:
        df["ExitTime"]=pd.to_datetime(df["ExitTime"],errors="coerce")
        df=df.dropna()
        df["Date"]=df["ExitTime"].dt.date
        df["Month"]=df["ExitTime"].dt.to_period("M")

        st.write("### Daily Revenue")
        st.bar_chart(df.groupby("Date")["Amount"].sum())

        st.write("### Monthly Revenue")
        st.bar_chart(df.groupby("Month")["Amount"].sum())
    else:
        st.info("No billing data available yet")
