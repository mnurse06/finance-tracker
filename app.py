import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FILES = {
    "transactions": DATA_DIR / "transactions.csv",
    "subscriptions": DATA_DIR / "subscriptions.csv",
    "cards": DATA_DIR / "cards.csv",
    "goals": DATA_DIR / "goals.csv",
}

def load_df(name, cols):
    fp = FILES[name]
    if fp.exists():
        df = pd.read_csv(fp)
        # ensure columns exist
        for c in cols:
            if c not in df.columns: df[c] = None
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_df(name, df):
    df.to_csv(FILES[name], index=False)

# ---------- Data ----------
tx_cols = ["id","date","amount","category","note"]
sub_cols = ["id","name","amount","cadence","next_charge_date","category"]
card_cols= ["id","name","limit","balance"]
goal_cols= ["id","name","target_amount","target_date","current_saved"]

tx   = load_df("transactions", tx_cols)
subs = load_df("subscriptions", sub_cols)
cards= load_df("cards", card_cols)
goals= load_df("goals", goal_cols)

st.set_page_config(page_title="Finance Tracker", layout="wide")

# ---------- Sidebar nav ----------
page = st.sidebar.radio("Navigate", ["Dashboard","Transactions","Subscriptions","Cards & Goals","Export"])

# ---------- Helpers ----------
def month_filter(df, date_col, y, m):
    if df.empty: return df
    d = pd.to_datetime(df[date_col], errors="coerce")
    return df[(d.dt.year==y) & (d.dt.month==m)]

# ---------- Pages ----------
if page == "Transactions":
    st.title("Transactions")
    with st.form("add_tx", clear_on_submit=True):
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            d = st.date_input("Date", value=date.today())
        with c2:
            amt = st.number_input("Amount (+ income, − expense)", step=1.0, format="%.2f")
        with c3:
            cat = st.selectbox("Category", ["Income","Rent","Food","Transport","Shopping","Bills","Other"])
        with c4:
            note = st.text_input("Note")
        submitted = st.form_submit_button("Add")
        if submitted:
            new = pd.DataFrame([{
                "id": len(tx)+1, "date": d.isoformat(), "amount": amt,
                "category": cat, "note": note
            }])
            tx = pd.concat([tx, new], ignore_index=True)
            save_df("transactions", tx)
            st.success("Transaction added.")

    st.subheader("All Transactions")
    st.dataframe(tx.sort_values("date", ascending=False), use_container_width=True)

elif page == "Subscriptions":
    st.title("Subscriptions")
    with st.form("add_sub", clear_on_submit=True):
        c1,c2,c3,c4 = st.columns(4)
        with c1: name = st.text_input("Name (e.g., Netflix)")
        with c2: amount = st.number_input("Amount", step=1.0, format="%.2f")
        with c3: cadence = st.selectbox("Cadence", ["monthly"])
        with c4: next_date = st.date_input("Next charge date", value=date.today())
        cat = st.selectbox("Category", ["Entertainment","Bills","Other"])
        submitted = st.form_submit_button("Add")
        if submitted and name:
            new = pd.DataFrame([{
                "id": len(subs)+1, "name": name, "amount": amount,
                "cadence": cadence, "next_charge_date": next_date.isoformat(),
                "category": cat
            }])
            subs = pd.concat([subs, new], ignore_index=True)
            save_df("subscriptions", subs)
            st.success("Subscription added.")

    st.subheader("Upcoming (this month)")
    today = date.today()
    up = pd.to_datetime(subs["next_charge_date"], errors="coerce")
    upcoming = subs[(up.dt.year==today.year) & (up.dt.month==today.month)]
    st.dataframe(upcoming, use_container_width=True)

elif page == "Cards & Goals":
    st.title("Credit Cards")
    with st.form("add_card", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1: nm = st.text_input("Card name")
        with c2: lim = st.number_input("Limit", step=100.0, format="%.2f")
        with c3: bal = st.number_input("Current balance", step=100.0, format="%.2f")
        submitted = st.form_submit_button("Add")
        if submitted and nm:
            new = pd.DataFrame([{"id": len(cards)+1,"name": nm,"limit": lim,"balance": bal}])
            cards = pd.concat([cards, new], ignore_index=True)
            save_df("cards", cards)
            st.success("Card added.")

    if not cards.empty:
        cards_display = cards.copy()
        cards_display["utilization"] = (cards_display["balance"]/cards_display["limit"]).fillna(0)
        st.dataframe(cards_display, use_container_width=True)
        total_util = (cards_display["balance"].sum()/cards_display["limit"].sum()) if cards_display["limit"].sum()>0 else 0
        st.metric("Total Credit Utilization", f"{total_util*100:.1f}%")
        if total_util > 0.3:
            st.warning("Tip: Utilization above 30% can hurt your score. Consider paying down balances before statement close.")

    st.markdown("---")
    st.title("Goals")
    with st.form("add_goal", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1: gname = st.text_input("Goal name (e.g., Emergency Fund)")
        with c2: tgt  = st.number_input("Target amount", step=100.0, format="%.2f")
        with c3: gdate= st.date_input("Target date")
        saved = st.number_input("Currently saved", step=50.0, format="%.2f")
        submitted = st.form_submit_button("Add")
        if submitted and gname:
            new = pd.DataFrame([{
                "id": len(goals)+1,"name": gname,"target_amount": tgt,
                "target_date": gdate.isoformat(),"current_saved": saved
            }])
            goals = pd.concat([goals, new], ignore_index=True)
            save_df("goals", goals)
            st.success("Goal added.")

    if not goals.empty:
        goals_display = goals.copy()
        goals_display["progress"] = (goals_display["current_saved"]/goals_display["target_amount"]).clip(0,1)
        for _,row in goals_display.iterrows():
            st.write(f"**{row['name']}** — {row['current_saved']:.0f}/{row['target_amount']:.0f}")
            st.progress(float(row["progress"]))

elif page == "Dashboard":
    st.title("Dashboard")
    y = st.number_input("Year", value=date.today().year, step=1)
    m = st.number_input("Month", value=date.today().month, min_value=1, max_value=12, step=1)

    month_tx = month_filter(tx, "date", int(y), int(m))
    income = month_tx[month_tx["amount"]>0]["amount"].sum()
    expense = -month_tx[month_tx["amount"]<0]["amount"].sum()
    st.metric("Income (month)", f"${income:,.2f}")
    st.metric("Expenses (month)", f"${expense:,.2f}")
    st.metric("Net (month)", f"${(income-expense):,.2f}")

    if not month_tx.empty:
        cat_sum = month_tx.groupby("category")["amount"].sum().sort_values()
        st.bar_chart(cat_sum)

    # Simple advice
    tips = []
    if expense > income and income > 0:
        tips.append("You're spending more than you earn this month—consider setting category budgets.")
    if not cards.empty and (cards["balance"].sum()/max(cards["limit"].sum(),1)) > 0.3:
        tips.append("Credit utilization is above 30%; paying before statement date may help score.")
    if not subs.empty and expense > 0 and len(subs) >= 3:
        tips.append("Review subscriptions—small recurring charges add up.")
    st.subheader("Advice")
    if tips:
        for t in tips: st.write("• " + t)
    else:
        st.write("Looking good! No alerts right now.")

elif page == "Export":
    st.title("Export Data")
    st.download_button("Download transactions.csv", tx.to_csv(index=False), "transactions.csv", "text/csv")
    st.download_button("Download subscriptions.csv", subs.to_csv(index=False), "subscriptions.csv", "text/csv")
    st.download_button("Download cards.csv", cards.to_csv(index=False), "cards.csv", "text/csv")
    st.download_button("Download goals.csv", goals.to_csv(index=False), "goals.csv", "text/csv")
