import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path

# -------------------------
# Basic setup & file wiring
# -------------------------
st.set_page_config(page_title="Finance Tracker", layout="wide")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FILES = {
    "transactions": DATA_DIR / "transactions.csv",
    "subscriptions": DATA_DIR / "subscriptions.csv",
    "cards": DATA_DIR / "cards.csv",
    "goals": DATA_DIR / "goals.csv",
    "budgets": DATA_DIR / "budgets.csv",   # NEW
}

CATEGORIES = ["Income", "Rent", "Food", "Transport", "Shopping", "Bills", "Other"]

def load_df(name, cols):
    fp = FILES[name]
    if fp.exists():
        df = pd.read_csv(fp)
        # ensure required columns exist
        for c in cols:
            if c not in df.columns:
                df[c] = None
        # keep only needed columns (and in order)
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_df(name, df):
    df.to_csv(FILES[name], index=False)

# ---------- Data models ----------
tx_cols    = ["id","date","amount","category","note"]
sub_cols   = ["id","name","amount","cadence","next_charge_date","category"]
card_cols  = ["id","name","limit","balance"]
goal_cols  = ["id","name","target_amount","target_date","current_saved"]
budget_cols= ["category","monthly_budget"]  # NEW

tx     = load_df("transactions", tx_cols)
subs   = load_df("subscriptions", sub_cols)
cards  = load_df("cards", card_cols)
goals  = load_df("goals", goal_cols)
budgets= load_df("budgets", budget_cols)     # NEW

# -------------------------
# Helpers
# -------------------------
def month_filter(df, date_col, y, m):
    if df.empty:
        return df
    d = pd.to_datetime(df[date_col], errors="coerce")
    return df[(d.dt.year == y) & (d.dt.month == m)]

def safe_category_index(value, options):
    try:
        return options.index(value)
    except Exception:
        return max(options.index("Other"), 0)

# -------------------------
# Sidebar navigation
# -------------------------
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard","Transactions","Subscriptions","Cards & Goals","Budgets","Export"]  # NEW: Budgets
)

# -------------------------
# Pages
# -------------------------
if page == "Transactions":
    st.title("Transactions")

    # Add form
    with st.form("add_tx", clear_on_submit=True):
        c1,c2,c3,c4 = st.columns(4)
        with c1: d = st.date_input("Date", value=date.today())
        with c2: amt = st.number_input("Amount (+ income, − expense)", step=1.0, format="%.2f")
        with c3: cat = st.selectbox("Category", CATEGORIES)
        with c4: note = st.text_input("Note")
        submitted = st.form_submit_button("Add")
        if submitted:
            new = pd.DataFrame([{
                "id": (tx["id"].max() + 1) if not tx.empty else 1,
                "date": d.isoformat(),
                "amount": amt,
                "category": cat,
                "note": note
            }])
            tx = pd.concat([tx, new], ignore_index=True)
            save_df("transactions", tx)
            st.success("Transaction added.")

    st.subheader("All Transactions")
    st.dataframe(tx.sort_values("date", ascending=False), use_container_width=True)

    # --- Transaction editor (NEW) ---
    st.subheader("Edit / Delete")
    if not tx.empty:
        row_id = st.selectbox("Pick a transaction ID to edit/delete", tx["id"].tolist())
        row = tx[tx["id"] == row_id].iloc[0]

        c1,c2,c3,c4 = st.columns(4)
        with c1:
            d_edit = st.date_input("Date", value=pd.to_datetime(row["date"]).date() if pd.notna(row["date"]) else date.today())
        with c2:
            amt_edit = st.number_input("Amount (+ income, − expense)", value=float(row["amount"]), step=1.0, format="%.2f")
        with c3:
            cat_edit = st.selectbox(
                "Category",
                CATEGORIES,
                index=safe_category_index(str(row["category"]), CATEGORIES)
            )
        with c4:
            note_edit = st.text_input("Note", value=str(row["note"]) if pd.notna(row["note"]) else "")

        c5, c6 = st.columns(2)
        if c5.button("Save changes"):
            tx.loc[tx["id"] == row_id, ["date","amount","category","note"]] = [
                d_edit.isoformat(), amt_edit, cat_edit, note_edit
            ]
            save_df("transactions", tx)
            st.success("Updated.")
            st.rerun()
        if c6.button("Delete transaction"):
            tx = tx[tx["id"] != row_id].reset_index(drop=True)
            # reassign IDs (optional)
            tx["id"] = range(1, len(tx) + 1)
            save_df("transactions", tx)
            st.success("Deleted.")
            st.rerun()

elif page == "Subscriptions":
    st.title("Subscriptions")

    # Add subscription
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
                "id": (subs["id"].max() + 1) if not subs.empty else 1,
                "name": name,
                "amount": amount,
                "cadence": cadence,
                "next_charge_date": next_date.isoformat(),
                "category": cat
            }])
            subs = pd.concat([subs, new], ignore_index=True)
            save_df("subscriptions", subs)
            st.success("Subscription added.")

    st.subheader("Upcoming (this month)")
    today = date.today()
    up = pd.to_datetime(subs["next_charge_date"], errors="coerce") if not subs.empty else pd.Series(dtype="datetime64[ns]")
    upcoming = subs[(up.dt.year==today.year) & (up.dt.month==today.month)] if not subs.empty else subs
    st.dataframe(upcoming, use_container_width=True)

    # NEW: Post this month's subscriptions to Transactions (with regex=False fix)
    st.markdown("### Post this month’s subscriptions to Transactions")
    if not subs.empty:
        if st.button("Add charges to Transactions"):
            up = pd.to_datetime(subs["next_charge_date"], errors="coerce")
            due = subs[(up.dt.year == today.year) & (up.dt.month == today.month)]
            added = 0
            for _, s in due.iterrows():
                marker = f"[sub:{s['name']}:{today.year}-{today.month:02d}]"
                # prevent duplicates by checking note marker EXACTLY (no regex)
                if not tx[tx["note"].fillna("").str.contains(marker, regex=False, na=False)].empty:
                    continue
                new = pd.DataFrame([{
                    "id": (tx["id"].max() + 1) if not tx.empty else 1,
                    "date": date(today.year, today.month, min(28, today.day)).isoformat(),
                    "amount": -abs(float(s["amount"])),
                    "category": s["category"],
                    "note": f"{s['name']} {marker}"
                }])
                tx = pd.concat([tx, new], ignore_index=True)
                added += 1
            save_df("transactions", tx)
            st.success(f"Posted {added} subscription charge(s) to Transactions.")
            st.rerun()

elif page == "Cards & Goals":
    st.title("Credit Cards")

    # Add card
    with st.form("add_card", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1: nm = st.text_input("Card name")
        with c2: lim = st.number_input("Limit", step=100.0, format="%.2f")
        with c3: bal = st.number_input("Current balance", step=100.0, format="%.2f")
        submitted = st.form_submit_button("Add")
        if submitted and nm:
            new = pd.DataFrame([{
                "id": (cards["id"].max() + 1) if not cards.empty else 1,
                "name": nm, "limit": lim, "balance": bal
            }])
            cards = pd.concat([cards, new], ignore_index=True)
            save_df("cards", cards)
            st.success("Card added.")

    if not cards.empty:
        cards_display = cards.copy()
        # avoid div-by-zero
        cards_display["utilization"] = (cards_display["balance"] / cards_display["limit"]).replace([pd.NA, pd.NaT], 0).fillna(0)
        st.dataframe(cards_display, use_container_width=True)
        total_util = (cards_display["balance"].sum()/cards_display["limit"].sum()) if cards_display["limit"].sum() > 0 else 0
        st.metric("Total Credit Utilization", f"{total_util*100:.1f}%")
        if total_util > 0.3:
            st.warning("Tip: Utilization above 30% can hurt your score. Consider paying down balances before statement close.")

    st.markdown("---")
    st.title("Goals")

    # Add goal
    with st.form("add_goal", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        with c1: gname = st.text_input("Goal name (e.g., Emergency Fund)")
        with c2: tgt  = st.number_input("Target amount", step=100.0, format="%.2f")
        with c3: gdate= st.date_input("Target date")
        saved = st.number_input("Currently saved", step=50.0, format="%.2f")
        submitted = st.form_submit_button("Add")
        if submitted and gname:
            new = pd.DataFrame([{
                "id": (goals["id"].max() + 1) if not goals.empty else 1,
                "name": gname, "target_amount": tgt,
                "target_date": gdate.isoformat(), "current_saved": saved
            }])
            goals = pd.concat([goals, new], ignore_index=True)
            save_df("goals", goals)
            st.success("Goal added.")

    if not goals.empty:
        goals_display = goals.copy()
        with pd.option_context('mode.use_inf_as_na', True):
            goals_display["progress"] = (goals_display["current_saved"] / goals_display["target_amount"]).clip(0, 1).fillna(0)
        for _, row in goals_display.iterrows():
            st.write(f"**{row['name']}** — {float(row['current_saved']):.0f}/{float(row['target_amount']):.0f}")
            st.progress(float(row["progress"]))

elif page == "Budgets":
    st.title("Budgets")

    with st.form("add_budget", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1: bcat = st.selectbox("Category", CATEGORIES[1:])  # skip "Income" for budgets
        with c2: blim = st.number_input("Monthly budget", step=10.0, format="%.2f")
        if st.form_submit_button("Add / Update"):
            if bcat:
                if budgets[budgets["category"] == bcat].empty:
                    budgets = pd.concat([budgets, pd.DataFrame([{"category": bcat, "monthly_budget": blim}])], ignore_index=True)
                else:
                    budgets.loc[budgets["category"] == bcat, "monthly_budget"] = blim
                save_df("budgets", budgets)
                st.success("Budget saved.")

    st.subheader("Current Budgets")
    st.dataframe(budgets, use_container_width=True)

elif page == "Dashboard":
    st.title("Dashboard")
    y = st.number_input("Year", value=date.today().year, step=1)
    m = st.number_input("Month", value=date.today().month, min_value=1, max_value=12, step=1)

    month_tx = month_filter(tx, "date", int(y), int(m))
    income = month_tx[month_tx["amount"] > 0]["amount"].sum() if not month_tx.empty else 0.0
    expense = -month_tx[month_tx["amount"] < 0]["amount"].sum() if not month_tx.empty else 0.0

    st.metric("Income (month)", f"${income:,.2f}")
    st.metric("Expenses (month)", f"${expense:,.2f}")
    st.metric("Net (month)", f"${(income - expense):,.2f}")

    if not month_tx.empty:
        cat_sum = month_tx.groupby("category")["amount"].sum().sort_values()
        st.bar_chart(cat_sum)

    # Budget comparison (expenses only)
    if not budgets.empty and not month_tx.empty:
        exp_by_cat = month_tx[month_tx["amount"] < 0].groupby("category")["amount"].sum().abs()
        st.subheader("Budget status (this month)")
        for _, row in budgets.iterrows():
            limit = float(row["monthly_budget"])
            spent = float(exp_by_cat.get(row["category"], 0.0))
            pct = min(spent/limit, 1.0) if limit > 0 else 0
            st.write(f"**{row['category']}** — ${spent:,.2f} of ${limit:,.2f}")
            st.progress(pct)
            if limit > 0 and spent > limit:
                st.warning(f"Over budget in {row['category']} by ${spent - limit:,.2f}.")

    # Smarter advice
    st.subheader("Advice")
    tips = []
    if expense > income and income > 0:
        tips.append("You're spending more than you earn this month—tighten categories or increase income.")
    if not cards.empty and (cards["balance"].sum()/max(cards["limit"].sum(),1)) > 0.3:
        tips.append("Credit utilization is above 30%; paying before statement date may help your score.")
    if not subs.empty and (len(subs) >= 3):
        tips.append("Audit subscriptions—cancel anything you don’t use to reduce recurring spend.")
    if not budgets.empty and not month_tx.empty:
        over = []
        exp_by_cat = month_tx[month_tx["amount"] < 0].groupby("category")["amount"].sum().abs()
        for _, r in budgets.iterrows():
            if float(exp_by_cat.get(r["category"], 0.0)) > float(r["monthly_budget"]):
                over.append(r["category"])
        if over:
            tips.append("Over budget in: " + ", ".join(over) + ". Consider moving discretionary spend to next month.")

    if tips:
        for t in tips:
            st.write("• " + t)
    else:
        st.write("Looking good! No alerts right now.")

elif page == "Export":
    st.title("Export Data")
    st.download_button("Download transactions.csv", tx.to_csv(index=False), "transactions.csv", "text/csv")
    st.download_button("Download subscriptions.csv", subs.to_csv(index=False), "subscriptions.csv", "text/csv")
    st.download_button("Download cards.csv", cards.to_csv(index=False), "cards.csv", "text/csv")
    st.download_button("Download goals.csv", goals.to_csv(index=False), "goals.csv", "text/csv")
    st.download_button("Download budgets.csv", budgets.to_csv(index=False), "budgets.csv", "text/csv")
