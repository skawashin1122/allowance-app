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

    return data


def save_data(data: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def initialize_session_state() -> None:
    if "data" not in st.session_state:
        st.session_state.data = load_data()


def main() -> None:
    initialize_session_state()

    st.title("💰 お小遣い＆バイト代管理帳")

    st.sidebar.header("サイドバー")
    st.sidebar.info("ここに目標設定やフィルターを追加予定です。")

    st.subheader("メインエリア")
    st.info("ここに今月サマリーや入力フォームを追加予定です。")

    st.subheader("データ状態（プレースホルダー）")
    st.write(st.session_state.data)


if __name__ == "__main__":
    main()
