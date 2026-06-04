import ctypes
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="台股 ETF 量化策略回測系統",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stMetric { background-color: #f8fafc; padding: 1.2rem; border-radius: 0.6rem; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; padding: 0.5rem 1.5rem; border-radius: 0.4rem; font-weight: 600; }
        .stTabs [aria-selected="true"] { background-color: #0284c7 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ 量化策略參數配置")

with st.sidebar.container(border=True):
    ticker_input = st.text_input("💎 投資標的組合 (以逗號分隔)", "0050.TW, 00878.TW, 00919.TW")
    tickers = [t.strip() for t in ticker_input.split(",")]
    num_assets = len(tickers)

    st.markdown("##### 📊 各成分股權重 (總和須為 1.0)")
    weights = []
    for i, ticker in enumerate(tickers):
        default_w = 1.0 / num_assets
        w = st.slider(f"{ticker} 權重", 0.0, 1.0, default_w, 0.05, key=f"w_{ticker}")
        weights.append(w)

    weight_sum = sum(weights)
    if abs(weight_sum - 1.0) > 0.001:
        st.error(f"⚠️ 權重總和: {weight_sum:.2f} (必須等於 1.0)")
        st.stop()
    else:
        st.caption("✅ 權重配置檢查通過")

with st.sidebar.container(border=True):
    base_monthly = st.number_input("💵 每月定期定額基礎預算 (TWD)", min_value=1000.0, value=20000.0, step=1000.0)
    ma_window = st.slider("📅 均線加碼週期 (MA Window 個月)", min_value=2, max_value=12, value=6)
    reinvest = st.checkbox("🔄 啟動股息再投入複利策略 (DRIP)", value=True)

st.title("📊 台股 ETF 混合架構動態策略回測系統")
st.caption("⚡ 系統核心：Python 後端數據處理與視覺化 + C++ 靜態編譯高效能記憶體定址引擎 (O(N) 複雜度)")

run_backtest = st.sidebar.button(" 執行量化回測", type="primary", use_container_width=True)

if True: 
    with st.spinner(" 正在向 Yahoo Finance 請求即時歷史數據並對齊時間軸..."):
        try:
            dfs = []
            for ticker in tickers:
                etf = yf.Ticker(ticker)
                hist = etf.history(period="3y", interval="1mo")
                hist = hist[['Close', 'Dividends']].copy()
                hist.columns = [f'Close_{ticker}', f'Div_{ticker}']
                dfs.append(hist)

            portfolio_df = pd.concat(dfs, axis=1).dropna()
            data_length = len(portfolio_df)
        except Exception as e:
            st.error(f"❌ 數據讀取失敗，請確認網路連線或 ETF 代碼是否正確。錯誤資訊: {e}")
            st.stop()

    if data_length == 0:
        st.warning(" 所選標的在過去 3 年內沒有共同的交易月份交集，請重新組合。")
        st.stop()

    flat_prices = []
    flat_dividends = []
    for ticker in tickers:
        flat_prices.extend(portfolio_df[f'Close_{ticker}'].tolist())
        flat_dividends.extend(portfolio_df[f'Div_{ticker}'].tolist())

    current_dir = os.path.dirname(os.path.abspath(__file__))
    dll_path = os.path.join(current_dir, "..", "cpp_engine", "engine.dll")
    
    if not os.path.exists(dll_path):
        st.error(f" 找不到核心編譯引擎 (engine.dll)，請先於 cpp_engine 目錄完成編譯。")
        st.stop()
        
    engine = ctypes.CDLL(dll_path)
    engine.calculate_portfolio_ma_strategy.argtypes = [
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
        ctypes.c_int, ctypes.c_int, ctypes.c_double,
        ctypes.c_int, ctypes.c_bool,
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)
    ]
    engine.calculate_portfolio_ma_strategy.restype = None
    c_prices = (ctypes.c_double * len(flat_prices))(*flat_prices)
    c_dividends = (ctypes.c_double * len(flat_dividends))(*flat_dividends)
    c_weights = (ctypes.c_double * num_assets)(*weights)

    out_total_cost = ctypes.c_double(0.0)
    out_final_value = ctypes.c_double(0.0)
    out_total_dividends = ctypes.c_double(0.0)
    c_history_assets = (ctypes.c_double * data_length)()
    c_history_cost = (ctypes.c_double * data_length)()

    engine.calculate_portfolio_ma_strategy(
        c_prices, c_dividends, c_weights,
        num_assets, data_length, base_monthly,
        ma_window, reinvest,
        ctypes.byref(out_total_cost), ctypes.byref(out_final_value), ctypes.byref(out_total_dividends),
        c_history_assets, c_history_cost
    )

    tc = out_total_cost.value
    fv = out_final_value.value
    td = out_total_dividends.value
    roi = (fv - tc) / tc if tc > 0 else 0
    
    assets_trend = np.array(list(c_history_assets))
    cost_trend = np.array(list(c_history_cost))
    
    running_max = np.maximum.accumulate(assets_trend)
    drawdown = (assets_trend - running_max) / running_max
    mdd_percentage = drawdown.min() * 100

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric(label="💰 實際總投入成本", value=f"{tc:,.0f} 元")
    m_col2.metric(label="📈 結算總資產市值", value=f"{fv:,.0f} 元")
    m_col3.metric(label="🎁 累計領取總股息", value=f"{td:,.0f} 元")
    roi_pct = roi * 100
    m_col4.metric(
        label="📊 策略總報酬率 (ROI)", 
        value=f"{roi_pct:+.2f}%", 
        delta=f"最大回撤 (MDD): {mdd_percentage:.2f}%", 
        delta_color="inverse"
    )

    st.markdown("---")

    tab_chart, tab_data = st.tabs(["📈 策略歷史軌跡趨勢圖", "📋 對齊歷史數據明細"])

    with tab_chart:
        st.subheader("資產增值曲線與水下回撤分析")
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.5), gridspec_kw={'height_ratios': [2.8, 1.2]})
        history_dates = portfolio_df.index
        ax1.plot(history_dates, assets_trend, label='Portfolio Market Value', color='#0284c7', linewidth=2.5)
        ax1.plot(history_dates, cost_trend, label='Total Invested Cost', color='#f97316', linestyle='--', linewidth=1.8)
        ax1.fill_between(history_dates, assets_trend, cost_trend, where=(assets_trend >= cost_trend), interpolate=True, color='#0284c7', alpha=0.08)
        ax1.set_ylabel("TWD ($)", fontsize=10, fontweight='bold')
        ax1.grid(True, linestyle=':', alpha=0.5)
        ax1.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='#e2e8f0')
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))
        ax1.tick_params(labelsize=9)

        ax2.fill_between(history_dates, drawdown * 100, 0, color='#ef4444', alpha=0.2)
        ax2.plot(history_dates, drawdown * 100, color='#dc2626', linewidth=1.2)
        ax2.set_ylabel("Drawdown (%)", fontsize=10, fontweight='bold')
        ax2.grid(True, linestyle=':', alpha=0.5)
        ax2.set_ylim([drawdown.min() * 100 * 1.2, 0])
        ax2.tick_params(labelsize=9)
        mdd_idx = np.argmin(drawdown)
        ax2.scatter(history_dates[mdd_idx], drawdown[mdd_idx] * 100, color='#b91c1c', s=35, zorder=5)
        ax2.text(history_dates[mdd_idx], drawdown[mdd_idx] * 100, f'  MDD: {mdd_percentage:.2f}%', color='#b91c1c', fontweight='bold', va='top', fontsize=9)
        plt.tight_layout()
        st.pyplot(fig)

    with tab_data:
        st.subheader("Pandas 多檔 ETF 日期交集清洗明細")
        st.caption("提示：以下為多檔 ETF 收盤價與當月發放股息（若當月未配息則顯示 0）的時間軸對齊數據。")
        display_df = portfolio_df.copy()
        display_df['策略累積成本'] = cost_trend
        display_df['策略資產總值'] = assets_trend
        st.dataframe(
            display_df.style.format("{:,.2f}").background_gradient(subset=['策略資產總值'], cmap='Blues'),
            use_container_width=True
        )
