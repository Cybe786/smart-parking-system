import streamlit as st
from datetime import datetime
import random
import csv
import os
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Smart Parking System", layout="wide")

PARKING_CSV = "parking_data.csv"
BILLING_CSV = "billing_data.csv"
INVOICE_DIR = "invoices"
os.makedirs(INVOICE_DIR, exist_ok=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"
RATE_PER_HOUR = 20
UPI_ID = "smartparking@upi"

# ---------------- LOGIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Smart Parking Admin Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid Credentials")
    st.stop()

if st.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ---------------- INIT CSV ----------------
if not os.path.exists(BILLING_CSV):
    with open(BILLING_CSV, "w", newline="") as f:
        csv.writer(f).writerow(
            ["Vehicle","Slot","EntryTime","ExitTime","Minutes","Amount","PaymentStatus"]
        )

# ---------------- SLOT STATE ----------------
if "slots" not in st.session_state:
    st.session_state.slots = {
        i: {"status": "Free", "vehicle": None, "entry_time": None}
        for i in range(1, 6)
    }

if "payment_pending" not in st.session_state:
    st.session_state.payment_pending = None

st.title("🅿 Smart Parking Management System")

# ---------------- DASHBOARD ----------------
total = len(st.session_state.slots)
free = sum(1 for s in st.session_state.slots.values() if s["status"] == "Free")
occupied = total - free

c1, c2, c3 = st.columns(3)
c1.metric("Total Slots", total)
c2.metric("Free Slots", free)
c3.metric("Occupied Slots", occupied)

st.divider()

# ---------------- LIVE STATUS ----------------
st.subheader("📊 Live Slot Status")
cols = st.columns(5)

for i,(slot,data) in enumerate(st.session_state.slots.items()):
    if data["status"] == "Free":
        cols[i].success(f"Slot {slot}\nFree")
    else:
        mins = int((datetime.now() - data["entry_time"]).total_seconds()/60)
        cols[i].error(f"Slot {slot}\n{data['vehicle']}\n{mins} min")

st.divider()

# ---------------- MANUAL ENTRY ----------------
st.subheader("🚗 Manual Entry")

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
        st.success("Vehicle Parked")
        st.rerun()
else:
    st.warning("Parking Full")

st.divider()

# ---------------- ANPR ----------------
st.subheader("📷 ANPR Simulation")

if st.button("Scan Number Plate"):
    plate = f"MH{random.randint(10,99)}AB{random.randint(1000,9999)}"
    free_slots_anpr = [s for s in st.session_state.slots if st.session_state.slots[s]["status"]=="Free"]

    if free_slots_anpr:
        slot = free_slots_anpr[0]
        now = datetime.now()
        st.session_state.slots[slot] = {
            "status":"Occupied",
            "vehicle":plate,
            "entry_time":now
        }
        st.success(f"Detected: {plate}")
        st.rerun()
    else:
        st.error("Parking Full")

st.divider()

# ---------------- EXIT + BILL ----------------
st.subheader("🚙 Exit & Billing")

exit_slot = st.selectbox("Select Slot to Exit", st.session_state.slots.keys())

if st.button("Process Exit"):
    data = st.session_state.slots[exit_slot]

    if data["status"]=="Occupied":
        exit_time = datetime.now()
        entry_time = data["entry_time"]

        minutes = int((exit_time-entry_time).total_seconds()/60)
        hours = max(1, minutes//60)
        amount = hours * RATE_PER_HOUR

        st.session_state.payment_pending = {
            "vehicle":data["vehicle"],
            "slot":exit_slot,
            "entry":entry_time,
            "exit":exit_time,
            "minutes":minutes,
            "amount":amount
        }

        st.session_state.slots[exit_slot] = {
            "status":"Free",
            "vehicle":None,
            "entry_time":None
        }
        st.rerun()

# ---------------- QR PAYMENT ----------------
if st.session_state.payment_pending:

    bill = st.session_state.payment_pending

    st.divider()
    st.subheader("💳 UPI Payment")

    st.info(f"Vehicle: {bill['vehicle']}")
    st.info(f"Amount: ₹{bill['amount']}")
    st.success(f"UPI ID: {UPI_ID}")

    qr_data = f"upi://pay?pa={UPI_ID}&pn=SmartParking&am={bill['amount']}&cu=INR"
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_data}", width=200)

    if st.button("✅ I Have Paid"):

        with open(BILLING_CSV,"a",newline="") as f:
            csv.writer(f).writerow([
                bill["vehicle"],
                bill["slot"],
                bill["entry"].isoformat(),
                bill["exit"].isoformat(),
                bill["minutes"],
                bill["amount"],
                "PAID"
            ])

        # PDF Invoice
        filename = f"{INVOICE_DIR}/invoice_{bill['vehicle']}_{bill['exit'].strftime('%Y%m%d_%H%M%S')}.pdf"
        c = canvas.Canvas(filename)
        c.drawString(100,800,"Parking Invoice")
        c.drawString(100,770,f"Vehicle: {bill['vehicle']}")
        c.drawString(100,750,f"Amount: ₹{bill['amount']}")
        c.save()

        with open(filename,"rb") as f:
            st.download_button("Download Invoice",f,file_name=os.path.basename(filename))

        st.success("Payment Successful")
        st.session_state.payment_pending=None
        st.rerun()

# ---------------- SAFE REVENUE SECTION ----------------
st.divider()
st.subheader("💰 Revenue Analytics")

if os.path.exists(BILLING_CSV):

    try:
        df = pd.read_csv(BILLING_CSV, on_bad_lines="skip")
    except:
        df = pd.DataFrame()

    if not df.empty and "ExitTime" in df.columns:

        df["ExitTime"] = pd.to_datetime(df["ExitTime"], errors="coerce")
        df = df.dropna(subset=["ExitTime"])

        total_revenue = df["Amount"].sum()

        today = datetime.now().date()
        daily_revenue = df[df["ExitTime"].dt.date==today]["Amount"].sum()

        df["Month"] = df["ExitTime"].dt.to_period("M")
        monthly_revenue = df.groupby("Month")["Amount"].sum()

        colA,colB = st.columns(2)
        colA.metric("Total Revenue", f"₹{total_revenue}")
        colB.metric("Today's Revenue", f"₹{daily_revenue}")

        st.line_chart(monthly_revenue)

    else:
        st.info("No valid revenue data available")
