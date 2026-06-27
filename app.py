import json
from pathlib import Path
from typing import Any

import streamlit as st

DATA_FILE = Path("allowance_data.json")
DEFAULT_DATA: dict[str, Any] = {"goal": 0, "transactions": []}


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

    return data


def save_data(data: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def initialize_session_state() -> None:
    if "data" not in st.session_state:
        st.session_state.data = load_data()
    if "goal_reached" not in st.session_state:
        st.session_state.goal_reached = False


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


def main() -> None:
    initialize_session_state()

    st.title("💰 お小遣い＆バイト代管理帳")

    data = st.session_state.data
    transactions = data["transactions"]
    goal = float(data["goal"])
    balance = calculate_balance(transactions)
    progress_ratio, percentage, is_goal_achieved = calculate_progress(balance, goal)

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

    st.subheader("データ状態")
    st.write(data)


if __name__ == "__main__":
    main()
