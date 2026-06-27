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
    if "input_date" not in st.session_state:
        st.session_state.input_date = date.today()
    if "input_type" not in st.session_state:
        st.session_state.input_type = "収入"
    if "input_category" not in st.session_state:
        st.session_state.input_category = INCOME_CATEGORIES[0]
    if "input_amount" not in st.session_state:
        st.session_state.input_amount = 0
    if "input_memo" not in st.session_state:
        st.session_state.input_memo = ""


def sync_category_with_type() -> None:
    transaction_type = st.session_state.input_type
    category_options = INCOME_CATEGORIES if transaction_type == "収入" else EXPENSE_CATEGORIES

    if st.session_state.input_category not in category_options:
        st.session_state.input_category = category_options[0]


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


def remove_transaction_by_id(
    transactions: list[dict[str, Any]],
    transaction_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError("transaction_id must be a non-empty string.")
    return [transaction for transaction in transactions if transaction["id"] != transaction_id]


def sort_transactions_for_display(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(transactions, key=lambda transaction: (transaction["date"], transaction["id"]), reverse=True)


def transactions_to_dataframe(transactions: list[dict[str, Any]]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=["id", "date", "type", "category", "amount", "memo"])

    dataframe = pd.DataFrame(transactions)
    dataframe["date"] = pd.to_datetime(dataframe["date"], format="%Y-%m-%d")
    dataframe["amount"] = dataframe["amount"].astype(float)
    return dataframe


def main() -> None:
    initialize_session_state()

    st.title("💰 お小遣い＆バイト代管理帳")
    balance_metric = st.empty()

    data = st.session_state.data
    st.subheader("収支を入力")
    transaction_date = st.date_input("日付", key="input_date")
    transaction_type = st.radio(
        "タイプ",
        ["収入", "支出"],
        horizontal=True,
        key="input_type",
        on_change=sync_category_with_type,
    )
    category_options = INCOME_CATEGORIES if transaction_type == "収入" else EXPENSE_CATEGORIES
    if st.session_state.input_category not in category_options:
        st.session_state.input_category = category_options[0]
    category = st.selectbox("カテゴリ", options=category_options, key="input_category")
    amount = st.number_input("金額（円）", min_value=0, step=100, key="input_amount")
    memo = st.text_input("メモ", key="input_memo")
    is_submitted = st.button("追加")

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
            st.session_state.input_date = date.today()
            st.session_state.input_amount = 0
            st.session_state.input_memo = ""

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
    if not transactions:
        st.info("まだ収支データがありません。フォームから追加してください。")
    else:
        header_columns = st.columns([1.4, 1.0, 1.2, 1.0, 2.0, 0.8])
        header_columns[0].markdown("**日付**")
        header_columns[1].markdown("**種別**")
        header_columns[2].markdown("**カテゴリ**")
        header_columns[3].markdown("**金額（円）**")
        header_columns[4].markdown("**メモ**")
        header_columns[5].markdown("**操作**")

        for transaction in sort_transactions_for_display(transactions):
            row_columns = st.columns([1.4, 1.0, 1.2, 1.0, 2.0, 0.8])
            row_columns[0].write(transaction["date"])
            row_columns[1].write(transaction["type"])
            row_columns[2].write(transaction["category"])
            row_columns[3].write(f"{float(transaction['amount']):,.0f}円")
            row_columns[4].write(transaction["memo"])

            if row_columns[5].button("削除", key=f"delete_{transaction['id']}"):
                data["transactions"] = remove_transaction_by_id(transactions, transaction["id"])
                st.session_state.data = data
                save_data(data)
                st.rerun()

    st.subheader("お小遣い分析")
    transaction_dataframe = transactions_to_dataframe(transactions)
    if transaction_dataframe.empty:
        st.info("データが登録されるとグラフが表示されます")
    else:
        expense_by_category = (
            transaction_dataframe[transaction_dataframe["type"] == "支出"]
            .groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
        )
        st.write("カテゴリ別支出")
        st.bar_chart(expense_by_category)

        balance_trend = (
            transaction_dataframe.sort_values(["date", "id"])
            .assign(
                signed_amount=lambda dataframe: dataframe["amount"].where(
                    dataframe["type"] == "収入",
                    -dataframe["amount"],
                )
            )
            .assign(balance=lambda dataframe: dataframe["signed_amount"].cumsum())
            .groupby("date")["balance"]
            .last()
        )
        balance_trend.index = balance_trend.index.date
        st.write("日々の累積残高推移")
        st.line_chart(balance_trend)


if __name__ == "__main__":
    main()
