# Taiwan ETF Backtester

這是一個結合 Python 與 C++ 的台股 ETF 定期定額回測工具。

開發這個專案的初衷，是為了解決純 Python 在處理「多檔資產時間軸對齊」與「動態均線策略」時的效能瓶頸。為了讓迴圈運算更有效率，我將核心的演算法用 C++ 實作，並透過 `ctypes` 讓 Python 進行底層呼叫，最後搭配 Streamlit 提供直覺的視覺化操作介面。

## 核心功能與技術實作

* **跨語言通訊 (FFI)**：Python 端負責呼叫 `yfinance` 抓取資料並用 Pandas 清洗對齊，接著將二維數據平坦化 (1D Flattening) 後，透過指標傳遞給 C++ 的 `engine.dll` 進行運算。
* **動態加碼策略**：C++ 引擎內建均線 (如 6MA 半年線) 計算邏輯。當系統偵測到當月股價跌破均線時，會自動觸發「逢低加碼」，將當月扣款金額翻倍。
* **風險控管視覺化**：除了基礎的總投入與 ROI，系統會同步計算「最大回撤 (MDD)」，並在前端繪製資產成長與回撤水下曲線 (Underwater Chart)。

## 系統環境需求

* Windows 64-bit OS
* Python 3.8+
* MinGW-w64 (GCC 64-bit 編譯器)

## 快速啟動

**1. 編譯 C++ 核心引擎** 請先進入 `cpp_engine` 目錄，透過靜態連結編譯出動態連結庫，避免後續執行時缺少依賴檔：

```bash
cd cpp_engine
g++ -shared -o engine.dll engine.cpp -static -static-libgcc -static-libstdc++
