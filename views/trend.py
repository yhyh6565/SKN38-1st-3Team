# trend_page 화면
import altair as alt
import pandas as pd
import streamlit as st

from utils.common import (
    aggregate,
    format_country,
    format_number,
    period_filter_controls,
    growth,
    header,
    format_metric_value,
    format_signed_total,
    state,
)
from utils.constants import (
    COUNTRIES,
    DATA_FIRST_MONTH,
    DATA_LAST_MONTH,
    MONTHS,
    MONTH_INDEX_BASE_YEAR,
    month_to_index,
)
from utils.data import load_dashboard_data


MONTHS_PER_YEAR = 12
FIRST_AVAILABLE_MONTH_INDEX = month_to_index(DATA_FIRST_MONTH)


def trend_page():
    # 1. 필터
    filters = period_filter_controls()
    start = filters["start"]
    end = filters["end"]
    header("01 전체 흐름", "자동차 부품 무역수지의 변화")
    (country_col,) = st.columns(1)
    with country_col:
        selected_country = st.selectbox(
            "대상 국가",
            ["10개국 전체"] + COUNTRIES,
            format_func=format_country,
            key="country",
        )
    country = "all" if selected_country == "10개국 전체" else selected_country
    place = "10개국 전체" if country == "all" else country

    # 2. 계산
    data = load_dashboard_data()
    current, previous = aggregate(start, end, country=country)
    export_sum = current["수출액"].sum()
    import_sum = current["수입액"].sum()
    previous_export_sum = previous["수출액"].sum()
    previous_import_sum = previous["수입액"].sum()
    balance = current["무역수지"].sum()
    unit = "$M"

    # 3. 지표 카드
    export_change = growth(export_sum, previous_export_sum)
    import_change = growth(import_sum, previous_import_sum)
    previous_balance = previous["무역수지"].sum()
    balance_change = balance - previous_balance
    if previous.empty:
        export_delta = "전년 비교 자료 없음"
        import_delta = "전년 비교 자료 없음"
        balance_delta = "전년 비교 자료 없음"
    else:
        export_delta = f"{format_metric_value(export_change)}% (작년 같은 기간 대비)"
        import_delta = f"{format_metric_value(import_change)}% (작년 같은 기간 대비)"
        balance_delta = (
            f"{format_metric_value(balance_change)} · {state(previous_balance, balance)}"
        )
    first, second, third = st.columns(3)
    first.metric(
        "수출액",
        f"{format_number(export_sum)} {unit}",
        export_delta,
        delta_color="normal",
        border=True,
    )
    second.metric(
        "수입액",
        f"{format_number(import_sum)} {unit}",
        import_delta,
        delta_color="normal",
        border=True,
    )
    third.metric(
        "무역수지",
        f"{format_signed_total(balance)} {unit}",
        balance_delta,
        delta_color="normal",
        border=True,
    )

    # 4. 차트
    st.subheader("월별 수출액과 수입액")
    st.caption(f"{unit} · 2021년은 11월부터 · 음영 = 선택한 기간")
    if country == "all":
        timeline = data
    else:
        timeline = data[data["나라"] == country]
    monthly = timeline.groupby(["k", "월"])[["수출액", "수입액"]].sum().reset_index()
    monthly["대상 국가"] = place
    melted = pd.melt(
        monthly,
        id_vars=["k", "월", "대상 국가"],
        value_vars=["수출액", "수입액"],
        var_name="구분",
        value_name="금액",
    )
    band_data = pd.DataFrame(
        {
            "시작": [month_to_index(MONTHS[start]) - 0.5],
            "끝": [month_to_index(MONTHS[end]) + 0.5],
        }
    )
    band = (
        alt.Chart(band_data)
        .mark_rect(opacity=0.12, color="#1d58b0", tooltip=False)
        .encode(x="시작:Q", x2="끝:Q")
    )
    first_axis_year = int(DATA_FIRST_MONTH[:4])
    last_axis_year = int(DATA_LAST_MONTH[:4])
    year_tick_values = [
        month_to_index(f"{year}.01")
        for year in range(first_axis_year, last_axis_year + 1)
    ]
    line = (
        alt.Chart(melted)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "k:Q",
                axis=alt.Axis(
                    title="연도",
                    values=year_tick_values,
                    labelExpr=f"datum.value/12+{MONTH_INDEX_BASE_YEAR}",
                ),
                scale=alt.Scale(
                    domain=[
                        month_to_index(f"{first_axis_year}.01"),
                        month_to_index(DATA_LAST_MONTH),
                    ]
                ),
            ),
            y=alt.Y("금액:Q", title=unit),
            color=alt.Color(
                "구분:N",
                title="",
                scale=alt.Scale(
                    domain=["수출액", "수입액"],
                    range=["#1d58b0", "#c8620f"],
                ),
            ),
            tooltip=[
                alt.Tooltip("대상 국가:N", title="대상 국가"),
                alt.Tooltip("월:N", title="월"),
                alt.Tooltip("구분:N", title="항목"),
                alt.Tooltip("금액:Q", format=",.1f", title=unit),
            ],
        )
    )
    st.altair_chart(band + line, width="stretch")

    st.subheader("해마다 같은 기간 무역수지")
    st.caption(f"{unit} · 무역수지 = 수출액 − 수입액")
    year_rows = []
    last_year = int(MONTHS[end][:4])
    first_year = int(DATA_FIRST_MONTH[:4])
    for year in range(first_year, last_year + 1):
        year_offset = MONTHS_PER_YEAR * (last_year - year)
        range_start = month_to_index(MONTHS[start]) - year_offset
        range_end = month_to_index(MONTHS[end]) - year_offset
        if range_start < FIRST_AVAILABLE_MONTH_INDEX:
            continue
        year_frame = data[(data["k"] >= range_start) & (data["k"] <= range_end)]
        if country != "all":
            year_frame = year_frame[year_frame["나라"] == country]
        yearly_balance = year_frame["무역수지"].sum()
        year_rows.append(
            {"연도": str(year), "대상 국가": place, "무역수지": yearly_balance}
        )
    yearly_frame = pd.DataFrame(year_rows)
    bars = (
        alt.Chart(yearly_frame)
        .mark_bar()
        .encode(
            x=alt.X("연도:N", title=None),
            y=alt.Y("무역수지:Q", title=unit),
            color=alt.condition(
                "datum['무역수지'] >= 0",
                alt.value("#1b7f52"),
                alt.value("#be3f33"),
            ),
            tooltip=[
                "연도:N",
                alt.Tooltip("대상 국가:N", title="대상 국가"),
                alt.Tooltip("무역수지:Q", format=",.1f", title=unit),
            ],
        )
    )
    labels = (
        alt.Chart(yearly_frame)
        .mark_text(dy=-8)
        .encode(
            x="연도:N",
            y="무역수지:Q",
            text=alt.Text("무역수지:Q", format=",.0f"),
            tooltip=[
                "연도:N",
                alt.Tooltip("대상 국가:N", title="대상 국가"),
                alt.Tooltip("무역수지:Q", format=",.1f", title=unit),
            ],
        )
    )
    st.altair_chart(bars + labels, width="stretch")
