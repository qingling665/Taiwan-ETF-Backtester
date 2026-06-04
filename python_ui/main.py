import ctypes
import os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

print("--- 🚀 啟動多檔 ETF 動態加碼視覺化回測引擎 ---")

tickers = ["0050.TW", "00878.TW", "00919.TW"]
weights = [0.4, 0.3, 0.3]
num_assets = len(tickers)

dfs = []
for ticker in tickers:
    etf = yf.Ticker(ticker)
    hist = etf.history(period="3y", interval="1mo")
    hist = hist[['Close', 'Dividends']].copy()
    hist.columns = [f'Close_{ticker}', f'Div_{ticker}']
    dfs.append(hist)

portfolio_df = pd.concat(dfs, axis=1).dropna()
data_length = len(portfolio_df)
print(f"✅ 成功對齊數據！共取得 {data_length} 個月的有效交易交集。\n")

flat_prices = []
flat_dividends = []
for ticker in tickers:
    flat_prices.extend(portfolio_df[f'Close_{ticker}'].tolist())
    flat_dividends.extend(portfolio_df[f'Div_{ticker}'].tolist())

current_dir = os.path.dirname(os.path.abspath(__file__))
dll_path = os.path.join(current_dir, "..", "cpp_engine", "engine.dll")
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

base_monthly = 20000.0
ma_window = 6
reinvest = True

engine.calculate_portfolio_ma_strategy(
    c_prices, c_dividends, c_weights,
    num_assets, data_length, base_monthly,
    ma_window, reinvest,
    ctypes.byref(out_total_cost), ctypes.byref(out_final_value), ctypes.byref(out_total_dividends),
    c_history_assets, c_history_cost # 傳入歷史紀錄通道
)

tc = out_total_cost.value
fv = out_final_value.value
td = out_total_dividends.value
roi = (fv - tc) / tc if tc > 0 else 0

print("="*45)
print(f"實際總投入成本: {tc:,.0f} 元")
print(f"最終投資組合價值: {fv:,.0f} 元")
print(f"總投資報酬率 (ROI): {roi * 100:.2f}%")
print("="*45)

import numpy as np

print("🎨 正在產生資產成長與最大回撤 (MDD) 雙層圖表...")

history_dates = portfolio_df.index
assets_trend = np.array(list(c_history_assets))
cost_trend = np.array(list(c_history_cost))
running_max = np.maximum.accumulate(assets_trend)
drawdown = (assets_trend - running_max) / running_max
mdd_percentage = drawdown.min() * 100

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
fig.suptitle(f"ETF Portfolio Dynamic Strategy ({', '.join(tickers)})", fontsize=16, fontweight='bold')

ax1.plot(history_dates, assets_trend, label='Market Value', color='#1f77b4', linewidth=2)
ax1.plot(history_dates, cost_trend, label='Invested Cost', color='#ff7f0e', linestyle='--')
ax1.fill_between(history_dates, assets_trend, cost_trend, where=(assets_trend >= cost_trend), interpolate=True, color='#1f77b4', alpha=0.1)
ax1.set_ylabel("Amount (TWD)", fontsize=11)
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.legend(loc='upper left')
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))

ax2.fill_between(history_dates, drawdown * 100, 0, color='#d62728', alpha=0.3)
ax2.plot(history_dates, drawdown * 100, color='#d62728', linewidth=1.5)
ax2.set_ylabel("Drawdown (%)", fontsize=11)
ax2.set_xlabel("Date", fontsize=11)
ax2.grid(True, linestyle=':', alpha=0.6)
ax2.set_ylim([drawdown.min() * 100 * 1.2, 0]) 
ax2.text(history_dates[np.argmin(drawdown)], drawdown.min() * 100, f' MDD: {mdd_percentage:.2f}%', color='darkred', fontweight='bold', va='top')

plt.tight_layout()
print(f"📉 歷史最大回撤 (MDD) 為: {mdd_percentage:.2f}%")
plt.show()