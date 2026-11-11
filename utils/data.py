"""GitHub에 포함된 CSV를 화면에서 쓰는 표 형식으로 변환한다."""
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.constants import COUNTRY_CODES, month_to_index
from utils.parts_catalog import ITEMS, PART_NAMES


CSV_PATH = (
    Path(__file__).resolve().parents[1]
    / "mysql_streamlit_app"
    / "database"
    / "hs8708_10countries.csv"
)


@st.cache_data(ttl=300)
def load_dashboard_data():
    frame = pd.read_csv(CSV_PATH, dtype={"hsCd": str, "statCd": str, "year": str})
    if frame.empty:
        st.error("저장소에 표시할 CSV 데이터가 없습니다.")
        st.stop()

    frame = frame.loc[
        frame["statCd"].isin(COUNTRY_CODES)
        & frame["hsCd"].ne("8708000000")
    ].copy()
    frame = frame.rename(columns={"expWgt": "expwgt", "impWgt": "impwgt"})

    for column in ["expDlr", "expwgt", "impDlr", "impwgt", "balPayments"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    named_codes = [code for code, name in ITEMS if code != "기타"]
    frame["부품 코드"] = frame["hsCd"].where(
        frame["hsCd"].isin(named_codes),
        "기타",
    )
    frame["부품"] = frame["부품 코드"].map(PART_NAMES)
    frame["나라"] = frame["statCd"].map(COUNTRY_CODES)
    frame["월"] = frame["year"]
    frame["k"] = frame["year"].map(month_to_index)
    frame["수출액"] = frame["expDlr"] / 1_000_000
    frame["수입액"] = frame["impDlr"] / 1_000_000
    frame["수출중량"] = frame["expwgt"] / 1_000
    frame["수입중량"] = frame["impwgt"] / 1_000
    frame["무역수지"] = frame["balPayments"] / 1_000_000

    dashboard_columns = [
        "월",
        "k",
        "부품 코드",
        "부품",
        "나라",
        "수출액",
        "수입액",
        "수출중량",
        "수입중량",
        "무역수지",
    ]
    return frame[dashboard_columns].groupby(
        ["월", "k", "부품 코드", "부품", "나라"],
        as_index=False,
        sort=False,
    ).sum()
