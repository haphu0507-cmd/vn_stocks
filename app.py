import streamlit as st
import pandas as pd
import numpy as np
# pyrefly: ignore [missing-import]
import plotly.graph_objects as go
# pyrefly: ignore [missing-import]
from plotly.subplots import make_subplots
from datetime import datetime

from data_loader import PRESET_GROUPS, get_stock_data, get_multiple_stocks_data
from indicators import calculate_indicators, evaluate_signal

# Page Config
st.set_page_config(
    page_title="VNIndex Stock Technical Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Glassmorphism & Vibrant Badges)
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .metric-val {
        font-size: 24px;
        font-weight: 700;
        margin-top: 4px;
    }
    .badge-bullish {
        background-color: #1b5e20;
        color: #81c784;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 13px;
    }
    .badge-bearish {
        background-color: #b71c1c;
        color: #ef9a9a;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 13px;
    }
    .badge-neutral {
        background-color: #424242;
        color: #e0e0e0;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'scan_df' not in st.session_state:
    st.session_state['scan_df'] = pd.DataFrame()
if 'stock_data_map' not in st.session_state:
    st.session_state['stock_data_map'] = {}
if 'last_scanned_tickers' not in st.session_state:
    st.session_state['last_scanned_tickers'] = []

# Title & Header
st.title("📈 VNIndex Stock Technical Analyzer")
st.caption(f"Hệ thống phân tích kỹ thuật cổ phiếu Việt Nam tự động • Cập nhật lúc {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}")

# Sidebar Options
st.sidebar.header("⚙️ Cấu Hình Động")

preset_name = st.sidebar.selectbox("Danh Mục Mã Mẫu", list(PRESET_GROUPS.keys()) + ["Tự chọn"])

if preset_name == "Tự chọn":
    default_list = ['FPT', 'HPG', 'VCB', 'SSI', 'VHM']
    selected_tickers = st.sidebar.multiselect("Chọn mã chứng khoán", options=PRESET_GROUPS["VN30"] + ['VND', 'DIG', 'HSG', 'FRT'], default=default_list)
else:
    preset_tickers = PRESET_GROUPS[preset_name]
    selected_tickers = st.sidebar.multiselect("Chọn mã chứng khoán", options=preset_tickers, default=preset_tickers)

time_frame = st.sidebar.selectbox("Khoảng Thời Gian Lấy Dữ Liệu", ["6 Tháng", "1 Năm", "2 Năm", "3 Năm"], index=1)
days_map = {"6 Tháng": 180, "1 Năm": 365, "2 Năm": 730, "3 Năm": 1095}
num_days = days_map[time_frame]

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Tùy Chọn Chỉ Báo Biểu Đồ")
show_ma20 = st.sidebar.checkbox("Hiển thị MA20", value=True)
show_ma50 = st.sidebar.checkbox("Hiển thị MA50", value=True)
show_ma200 = st.sidebar.checkbox("Hiển thị MA200", value=True)
show_bb = st.sidebar.checkbox("Dải Bollinger Bands", value=True)
show_rsi = st.sidebar.checkbox("Chỉ báo RSI", value=True)
show_macd = st.sidebar.checkbox("Chỉ báo MACD", value=True)

st.sidebar.markdown("---")
analyze_btn = st.sidebar.button("🚀 Phân Tích Kỹ Thuật", use_container_width=True, type="primary")

# Execute Analysis
if analyze_btn or st.session_state['scan_df'].empty:
    if not selected_tickers:
        st.warning("⚠️ Vui lòng chọn ít nhất 1 mã chứng khoán.")
    else:
        with st.spinner(f"Đang tải và tính toán dữ liệu cho {len(selected_tickers)} mã cổ phiếu..."):
            raw_data_map = get_multiple_stocks_data(selected_tickers, days=num_days)
            
            processed_map = {}
            summary_list = []
            
            for ticker, df in raw_data_map.items():
                if not df.empty and len(df) >= 5:
                    df_ind = calculate_indicators(df)
                    processed_map[ticker] = df_ind
                    
                    last_row = df_ind.iloc[-1]
                    sig_info = evaluate_signal(last_row)
                    
                    summary_list.append({
                        "Symbol": ticker,
                        "Giá Hiện Tại": last_row['close'],
                        "Thay Đổi (1D %)": round(last_row.get('change_1d', 0), 2),
                        "Thay Đổi (1W %)": round(last_row.get('change_1w', 0), 2),
                        "Thay Đổi (1M %)": round(last_row.get('change_1m', 0), 2),
                        "MA20": round(last_row.get('MA20', np.nan), 1) if pd.notna(last_row.get('MA20')) else None,
                        "MA50": round(last_row.get('MA50', np.nan), 1) if pd.notna(last_row.get('MA50')) else None,
                        "MA200": round(last_row.get('MA200', np.nan), 1) if pd.notna(last_row.get('MA200')) else None,
                        "RSI(14)": round(last_row.get('RSI', np.nan), 1) if pd.notna(last_row.get('RSI')) else None,
                        "Tín Hiệu": sig_info["Signal"],
                        "Chi Tiết": sig_info["Badges"]
                    })
            
            if summary_list:
                st.session_state['scan_df'] = pd.DataFrame(summary_list)
                st.session_state['stock_data_map'] = processed_map
                st.session_state['last_scanned_tickers'] = selected_tickers
            else:
                st.error("❌ Không lấy được dữ liệu cho các mã đã chọn.")

# Display Dashboard Layout
scan_df = st.session_state.get('scan_df', pd.DataFrame())
data_map = st.session_state.get('stock_data_map', {})

if not scan_df.empty:
    # KPI Summary Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_scanned = len(scan_df)
    bullish_cnt = len(scan_df[scan_df['Tín Hiệu'].str.contains("Tăng", na=False)])
    bearish_cnt = len(scan_df[scan_df['Tín Hiệu'].str.contains("Giảm", na=False)])
    neutral_cnt = total_scanned - bullish_cnt - bearish_cnt
    
    top_gainer = scan_df.sort_values(by="Thay Đổi (1D %)", ascending=False).iloc[0]
    
    col1.metric("Tổng Số Mã", f"{total_scanned} Mã")
    col2.metric("Mã Tăng Giá 🟢", f"{bullish_cnt}", f"{round(bullish_cnt/total_scanned*100, 1)}%")
    col3.metric("Mã Giảm Giá 🔴", f"{bearish_cnt}", f"-{round(bearish_cnt/total_scanned*100, 1)}%")
    col4.metric("Đi Ngang ⚪", f"{neutral_cnt}")
    col5.metric("Top Tăng Giá 🚀", f"{top_gainer['Symbol']}", f"+{top_gainer['Thay Đổi (1D %)']}%")

    st.markdown("---")

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Bảng Tín Hiệu Screener", "📈 Biểu Đồ Kỹ Thuật Chi Tiết", "⚖️ So Sánh Hiệu Suất"])

    # TAB 1: SCREENER TABLE
    with tab1:
        st.subheader("Bảng Tổng Hợp Tín Hiệu Kỹ Thuật")
        
        # Filter options
        signal_filter = st.radio(
            "Lọc Theo Tín Hiệu:", 
            ["Tất cả", "Tăng mạnh / Tăng giá", "Giảm mạnh / Giảm giá", "Trung tính"],
            horizontal=True
        )
        
        filtered_df = scan_df.copy()
        if signal_filter == "Tăng mạnh / Tăng giá":
            filtered_df = filtered_df[filtered_df['Tín Hiệu'].str.contains("Tăng", na=False)]
        elif signal_filter == "Giảm mạnh / Giảm giá":
            filtered_df = filtered_df[filtered_df['Tín Hiệu'].str.contains("Giảm", na=False)]
        elif signal_filter == "Trung tính":
            filtered_df = filtered_df[filtered_df['Tín Hiệu'] == "Trung tính"]

        # Styled Table Display
        st.dataframe(
            filtered_df.style.format({
                "Giá Hiện Tại": "{:,.0f}",
                "Thay Đổi (1D %)": "{:+.2f}%",
                "Thay Đổi (1W %)": "{:+.2f}%",
                "Thay Đổi (1M %)": "{:+.2f}%",
                "RSI(14)": "{:.1f}",
                "MA20": "{:,.0f}",
                "MA50": "{:,.0f}",
                "MA200": "{:,.0f}"
            }).map(
                lambda val: 'color: #00c853; font-weight: bold;' if isinstance(val, (int, float)) and val > 0 else ('color: #d50000; font-weight: bold;' if isinstance(val, (int, float)) and val < 0 else ''),
                subset=["Thay Đổi (1D %)", "Thay Đổi (1W %)", "Thay Đổi (1M %)"]
            ),
            use_container_width=True,
            height=450
        )

    # TAB 2: DETAILED CHART (Plotly Candlestick + Indicators)
    with tab2:
        st.subheader("Biểu Đồ Kỹ Thuật Tương Tác (TradingView Style)")
        
        available_symbols = list(data_map.keys())
        if available_symbols:
            selected_symbol = st.selectbox("Chọn Mã Cổ Phiếu Xem Chi Tiết:", available_symbols, index=0)
            
            df_chart = data_map[selected_symbol].copy()
            
            if not df_chart.empty:
                latest = df_chart.iloc[-1]
                
                # Header Metrics for Selected Stock
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Giá Khớp Lệnh", f"{latest['close']:,.0f} VNĐ", f"{latest.get('change_1d', 0):+.2f}%")
                c2.metric("Khối Lượng 1D", f"{int(latest['volume']):,}")
                c3.metric("RSI (14)", f"{latest.get('RSI', 0):.1f}")
                c4.metric("MA50 / MA200", f"{latest.get('MA50', 0):,.0f} / {latest.get('MA200', 0):,.0f}")
                c5.metric("Tín Hiệu MACD", "MUA" if latest.get('MACD', 0) > latest.get('MACD_Signal', 0) else "BÁN")
                
                # Determine rows count based on checkboxes
                row_heights = [0.6]
                subplot_titles = [f"{selected_symbol} - Giá & Khối Lượng"]
                specs = [[{"secondary_y": True}]]
                rows_cnt = 1
                
                if show_rsi:
                    rows_cnt += 1
                    row_heights.append(0.2)
                    subplot_titles.append("RSI (14)")
                    specs.append([{"secondary_y": False}])
                    
                if show_macd:
                    rows_cnt += 1
                    row_heights.append(0.2)
                    subplot_titles.append("MACD (12, 26, 9)")
                    specs.append([{"secondary_y": False}])

                # Normalize row heights sum to 1.0
                total_h = sum(row_heights)
                row_heights = [h / total_h for h in row_heights]
                
                fig = make_subplots(
                    rows=rows_cnt, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    subplot_titles=subplot_titles,
                    row_heights=row_heights,
                    specs=specs
                )
                
                # 1. Candlestick Chart
                fig.add_trace(
                    go.Candlestick(
                        x=df_chart['time'],
                        open=df_chart['open'],
                        high=df_chart['high'],
                        low=df_chart['low'],
                        close=df_chart['close'],
                        name="OHLC",
                        increasing_line_color='#00c853',
                        decreasing_line_color='#d50000'
                    ),
                    row=1, col=1
                )
                
                # Moving Averages & Bollinger Bands Overlays
                if show_ma20 and 'MA20' in df_chart:
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['MA20'], mode='lines', name='MA20', line=dict(color='#ff9800', width=1.5)), row=1, col=1)
                if show_ma50 and 'MA50' in df_chart:
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['MA50'], mode='lines', name='MA50', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
                if show_ma200 and 'MA200' in df_chart:
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['MA200'], mode='lines', name='MA200', line=dict(color='#e91e63', width=2)), row=1, col=1)
                
                if show_bb and 'BB_Upper' in df_chart:
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['BB_Upper'], mode='lines', name='BB Upper', line=dict(color='rgba(156, 39, 176, 0.4)', width=1, dash='dot')), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['BB_Lower'], mode='lines', name='BB Lower', line=dict(color='rgba(156, 39, 176, 0.4)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(156, 39, 176, 0.05)'), row=1, col=1)

                # Volume Bar Chart (Secondary Y-axis)
                colors = ['#00c853' if c >= o else '#d50000' for c, o in zip(df_chart['close'], df_chart['open'])]
                fig.add_trace(
                    go.Bar(x=df_chart['time'], y=df_chart['volume'], name="Khối lượng", marker_color=colors, opacity=0.3),
                    row=1, col=1, secondary_y=True
                )

                # 2. RSI Subplot
                curr_row = 2
                if show_rsi and 'RSI' in df_chart:
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['RSI'], mode='lines', name='RSI', line=dict(color='#9c27b0', width=1.5)), row=curr_row, col=1)
                    fig.add_shape(type="line", x0=df_chart['time'].iloc[0], y0=70, x1=df_chart['time'].iloc[-1], y1=70, line=dict(color="#d50000", width=1, dash="dash"), row=curr_row, col=1)
                    fig.add_shape(type="line", x0=df_chart['time'].iloc[0], y0=30, x1=df_chart['time'].iloc[-1], y1=30, line=dict(color="#00c853", width=1, dash="dash"), row=curr_row, col=1)
                    fig.update_yaxes(range=[0, 100], row=curr_row, col=1)
                    curr_row += 1

                # 3. MACD Subplot
                if show_macd and 'MACD' in df_chart:
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['MACD'], mode='lines', name='MACD', line=dict(color='#2196f3', width=1.5)), row=curr_row, col=1)
                    fig.add_trace(go.Scatter(x=df_chart['time'], y=df_chart['MACD_Signal'], mode='lines', name='Signal', line=dict(color='#ff9800', width=1.5)), row=curr_row, col=1)
                    hist_colors = ['#00c853' if h >= 0 else '#d50000' for h in df_chart['MACD_Hist']]
                    fig.add_trace(go.Bar(x=df_chart['time'], y=df_chart['MACD_Hist'], name='Histogram', marker_color=hist_colors, opacity=0.6), row=curr_row, col=1)

                # Layout styling
                fig.update_layout(
                    height=750,
                    template="plotly_dark",
                    margin=dict(l=40, r=40, t=40, b=40),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis_rangeslider_visible=False
                )
                fig.update_yaxes(title_text="Giá (VNĐ)", row=1, col=1, secondary_y=False)
                fig.update_yaxes(title_text="Khối lượng", showgrid=False, row=1, col=1, secondary_y=True)

                st.plotly_chart(fig, use_container_width=True)

    # TAB 3: STOCK COMPARISON (% Return Normalization)
    with tab3:
        st.subheader("So Sánh Tăng Trưởng Tương Đối (% Return)")
        
        selected_compare = st.multiselect("Chọn các mã cổ phiếu để so sánh:", available_symbols, default=available_symbols[:5] if len(available_symbols) >= 5 else available_symbols)
        
        if selected_compare:
            fig_comp = go.Figure()
            
            for sym in selected_compare:
                if sym in data_map:
                    df_sym = data_map[sym].copy()
                    if not df_sym.empty:
                        # Normalize to base 100 (%)
                        base_price = df_sym['close'].iloc[0]
                        df_sym['return_pct'] = ((df_sym['close'] / base_price) - 1) * 100
                        
                        fig_comp.add_trace(
                            go.Scatter(
                                x=df_sym['time'],
                                y=df_sym['return_pct'],
                                mode='lines',
                                name=sym,
                                line=dict(width=2)
                            )
                        )
            
            fig_comp.update_layout(
                title="Tỷ Lệ Tăng Trưởng (%) Tương Đối So Với Đầu Kỳ",
                xaxis_title="Thời gian",
                yaxis_title="Biến động (%)",
                template="plotly_dark",
                height=500,
                legend=dict(orientation="h", y=1.1)
            )
            
            st.plotly_chart(fig_comp, use_container_width=True)
