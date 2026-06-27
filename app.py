import json
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st

DATA_FILE = Path("allowance_data.json")
DEFAULT_DATA: dict[str, Any] = {"goal": 0, "transactions": []}
INCOME_CATEGORIES = ["お小遣い", "バイト代", "お年玉・お祝い", "その他"]
EXPENSE_CATEGORIES = ["買い食い", "ゲーム・ホビー", "洋服・美容", "友達との遊び", "勉強・本", "その他"]


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return DEFAULT_DATA.copy()

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("allowance_data.json must contain a JSON object.")

    if "goal" not in data or "transactions" not in data:
        raise ValueError("allowance_data.json must include 'goal' and 'transactions'.")

    if not isinstance(data["goal"], (int, float)):
        raise ValueError("'goal' must be a number.")

    if not isinstance(data["transactions"], list):
        raise ValueError("'transactions' must be a list.")

    for transaction in data["transactions"]:
        validate_transaction(transaction)

    return data


def save_data(data: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def initialize_session_state() -> None:
    if "data" not in st.session_state:
        st.session_state.data = load_data()
    if "goal_reached" not in st.session_state:
        st.session_state.goal_reached = False


def validate_transaction(transaction: Any) -> None:
    if not isinstance(transaction, dict):
        raise ValueError("Each transaction must be an object.")

    required_keys = {"id", "date", "type", "category", "amount", "memo"}
    if not required_keys.issubset(transaction.keys()):
        raise ValueError("Each transaction must include id/date/type/category/amount/memo.")

    transaction_id = transaction["id"]
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError("Each transaction 'id' must be a non-empty string.")

    transaction_date = transaction["date"]
    if not isinstance(transaction_date, str) or not transaction_date.strip():
        raise ValueError("Each transaction 'date' must be a non-empty string.")

    transaction_type = transaction["type"]
    if transaction_type not in {"収入", "支出"}:
        raise ValueError("Each transaction 'type' must be either '収入' or '支出'.")

    category = transaction["category"]
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Each transaction 'category' must be a non-empty string.")

    allowed_categories = INCOME_CATEGORIES if transaction_type == "収入" else EXPENSE_CATEGORIES
    if category not in allowed_categories:
        raise ValueError("Each transaction 'category' must match the selected transaction type.")

    amount = transaction["amount"]
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("Each transaction 'amount' must be a number greater than 0.")

    memo = transaction["memo"]
    if not isinstance(memo, str):
        raise ValueError("Each transaction 'memo' must be a string.")


def create_transaction(
    transaction_date: date,
    transaction_type: str,
    category: str,
    amount: int,
    memo: str,
) -> dict[str, Any]:
    transaction = {
        "id": str(uuid4()),
        "date": transaction_date.isoformat(),
        "type": transaction_type,
        "category": category,
        "amount": int(amount),
        "memo": memo.strip(),
    }
    validate_transaction(transaction)
    return transaction


def calculate_balance(transactions: list[dict[str, Any]]) -> float:
    balance = 0.0
    for transaction in transactions:
        transaction_type = transaction.get("type")
        amount = transaction.get("amount", 0)

        if not isinstance(amount, (int, float)):
            raise ValueError("Each transaction 'amount' must be a number.")

        if transaction_type == "収入":
            balance += amount
        elif transaction_type == "支出":
            balance -= amount
        else:
            raise ValueError("Each transaction 'type' must be either '収入' or '支出'.")

    return balance


def calculate_progress(balance: float, goal: float) -> tuple[float, float, bool]:
    if goal <= 0:
        return 0.0, 0.0, False

    raw_ratio = balance / goal
    progress_ratio = max(0.0, min(raw_ratio, 1.0))
    percentage = max(0.0, raw_ratio * 100)
    is_goal_achieved = raw_ratio >= 1.0
    return progress_ratio, percentage, is_goal_achieved


def build_transactions_dataframe(transactions: list[dict[str, Any]]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=["日付", "種別", "カテゴリ", "金額（円）", "メモ"])

    dataframe = pd.DataFrame(transactions)
    dataframe = dataframe.sort_values(by=["date", "id"], ascending=[False, False]).reset_index(drop=True)
    dataframe = dataframe[["date", "type", "category", "amount", "memo"]].rename(
        columns={
            "date": "日付",
            "type": "種別",
            "category": "カテゴリ",
            "amount": "金額（円）",
            "memo": "メモ",
        }
    )
    return dataframe


def main() -> None:
    initialize_session_state()

    st.title("💰 お小遣い＆バイト代管理帳")
    balance_metric = st.empty()

    data = st.session_state.data
    st.subheader("収支を入力")
    with st.form("transaction_form", clear_on_submit=True):
        transaction_date = st.date_input("日付", value=date.today())
        transaction_type = st.radio("タイプ", ["収入", "支出"], horizontal=True)
        category_options = INCOME_CATEGORIES if transaction_type == "収入" else EXPENSE_CATEGORIES
        category = st.selectbox("カテゴリ", options=category_options)
        amount = st.number_input("金額（円）", min_value=0, step=100, value=0)
        memo = st.text_input("メモ")
        is_submitted = st.form_submit_button("追加")

    if is_submitted:
        if amount <= 0:
            st.error("金額は1円以上で入力してください。")
        else:
            new_transaction = create_transaction(
                transaction_date=transaction_date,
                transaction_type=transaction_type,
                category=category,
                amount=int(amount),
                memo=memo,
            )
            data["transactions"].append(new_transaction)
            st.session_state.data = data
            save_data(data)
            st.success("収支データを追加しました。")

    transactions = data["transactions"]
    goal = float(data["goal"])
    balance = calculate_balance(transactions)
    progress_ratio, percentage, is_goal_achieved = calculate_progress(balance, goal)
    balance_metric.metric("合計残高", f"{balance:,.0f}円")

    st.sidebar.header("貯金目標")
    updated_goal = st.sidebar.number_input(
        "目標金額（円）",
        min_value=0,
        step=100,
        value=int(goal),
    )
    if updated_goal != int(goal):
        data["goal"] = int(updated_goal)
        st.session_state.data = data
        save_data(data)
        goal = float(updated_goal)
        progress_ratio, percentage, is_goal_achieved = calculate_progress(balance, goal)

    st.sidebar.write(f"現在の残高: {balance:,.0f}円")
    st.sidebar.write(f"達成率: {percentage:.1f}%")
    st.sidebar.progress(progress_ratio)
    if goal <= 0:
        st.sidebar.info("目標金額を設定すると達成率が表示されます。")

    if is_goal_achieved and not st.session_state.goal_reached:
        st.balloons()
    st.session_state.goal_reached = is_goal_achieved

    st.subheader("今月のサマリー")
    col1, col2 = st.columns(2)
    col1.metric("現在の残高", f"{balance:,.0f}円")
    col2.metric("貯金目標", f"{goal:,.0f}円")

    st.subheader("収支履歴")
    history_df = build_transactions_dataframe(transactions)
    if history_df.empty:
        st.info("まだ収支データがありません。フォームから追加してください。")
    else:
        st.dataframe(history_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
