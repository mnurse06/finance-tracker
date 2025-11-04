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
    "budgets": DATA_DIR / "budgets.csv",
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
budget_cols= ["category","monthly_budget"]

tx      = load_df("transactions", tx_cols)
subs    = load_df("subscriptions", sub_cols)
cards   = load_df("cards", card_cols)
goals   = load_df("goals", goal_cols)
budgets = load_df("budgets", budget_cols)

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

def next_id(df, col="id"):
    return int(df[col].max() + 1) if not df.empty else 1

# -------------------------
# Sidebar navigation
# -------------------------
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard","Transactions","Subscriptions","Cards & Goals","Budgets","Export"]
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
                "id": next_id(tx),
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

    # --- Transaction editor ---
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
                "id": next_id(subs),
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

    # Post this month's subscriptions to Transactions (regex=False fix)
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
                    "id": next_id(tx),
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
                "id": next_id(cards),
                "name": nm, "limit": lim, "balance": bal
            }])
            cards = pd.concat([cards, new], ignore_index=True)
            save_df("cards", cards)
            st.success("Card added.")

    if not cards.empty:
        cards_display = cards.copy()
        # avoid div-by-zero
        with pd.option_context('mode.use_inf_as_na', True):
            cards_display["utilization"] = (cards_display["balance"] / cards_display["limit"]).fillna(0)
        st.dataframe(cards_display, use_container_width=True)

        total_util = (cards_display["balance"].sum()/cards_display["limit"].sum()) if cards_display["limit"].sum() > 0 else 0
        st.metric("Total Credit Utilization", f"{total_util*100:.1f}%")
        if total_util > 0.3:
            st.warning("Tip: Utilization above 30% can hurt your score. Consider paying down balances before statement close.")
        else:
            st.info("Good: Total utilization under 30%.")

        # ===== Card Editor (edit name/limit/balance, or delete) =====
        st.subheader("Edit / Delete Card")
        def _fmt(i):
            row = cards.loc[cards["id"] == i]
            if row.empty: 
                return f"ID {i}"
            nm = str(row["name"].values[0]) if pd.notna(row["name"].values[0]) else f"ID {i}"
            return f"{nm} (ID {i})"

        card_choice = st.selectbox(
            "Choose a card to edit",
            cards["id"].tolist(),
            format_func=_fmt
        )

        row = cards[cards["id"] == card_choice].iloc[0]

        c1, c2, c3 = st.columns(3)
        with c1:
            edit_name = st.text_input("Card name", value=str(row["name"]) if pd.notna(row["name"]) else "")
        with c2:
            edit_limit = st.number_input(
                "Credit limit",
                value=float(row["limit"]) if pd.notna(row["limit"]) else 0.0,
                step=100.0,
                format="%.2f"
            )
        with c3:
            edit_balance = st.number_input(
                "Current balance",
                value=float(row["balance"]) if pd.notna(row["balance"]) else 0.0,
                step=50.0,
                format="%.2f"
            )

        a, b = st.columns(2)
        if a.button("Save card changes"):
            cards.loc[cards["id"] == card_choice, ["name", "limit", "balance"]] = [
                edit_name, edit_limit, edit_balance
            ]
            save_df("cards", cards)
            st.success("Card updated.")
            st.rerun()

        if b.button("Delete this card"):
            cards = cards[cards["id"] != card_choice].reset_index(drop=True)
            if not cards.empty:
                cards["id"] = range(1, len(cards) + 1)
            save_df("cards", cards)
            st.success("Card deleted.")
            st.rerun()

        # ===== Record a Payment (updates balance + creates a Transaction) =====
        st.subheader("Record a Payment")
        if not cards.empty:
            pay_card_choice = st.selectbox(
                "Select a card to pay",
                cards["id"].tolist(),
                format_func=_fmt,
                key="pay_card_choice"
            )
            pay_row = cards[cards["id"] == pay_card_choice].iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                pay_date = st.date_input("Payment date", value=date.today(), key="pay_date")
            with c2:
                max_pay = float(pay_row["balance"]) if pd.notna(pay_row["balance"]) else 0.0
                pay_amt = st.number_input(
                    "Payment amount",
                    min_value=0.0,
                    max_value=max(0.0, max_pay),
                    value=min(50.0, max_pay),
                    step=10.0,
                    format="%.2f",
                    key="pay_amt"
                )
            with c3:
                pay_note = st.text_input("Note (optional)", value="Credit card payment", key="pay_note")

            if st.button("Apply payment"):
                # 1) Update the card balance (cannot go below zero)
                new_bal = max(float(pay_row["balance"]) - float(pay_amt), 0.0)
                cards.loc[cards["id"] == pay_card_choice, "balance"] = new_bal
                save_df("cards", cards)

                # 2) Create a matching Transaction (cash outflow)
                marker = f"[ccpay:{pay_row['name']}:{pay_date.year}-{pay_date.month:02d}]"
                new_tx = pd.DataFrame([{
                    "id": next_id(tx),
                    "date": pay_date.isoformat(),
                    "amount": -abs(float(pay_amt)),   # payment is an outflow
                    "category": "Bills",
                    "note": f"CC Payment - {pay_row['name']} {marker} {pay_note}".strip()
                }])
                tx = pd.concat([tx, new_tx], ignore_index=True)
                save_df("transactions", tx)

                st.success(f"Applied ${pay_amt:,.2f} payment to {pay_row['name']}. New balance: ${new_bal:,.2f}")
                st.rerun()

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
                "id": next_id(goals),
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
