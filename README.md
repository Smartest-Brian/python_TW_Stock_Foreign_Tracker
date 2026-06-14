# Taiwan Stock & Foreign Institutional Tracker

An interactive, premium-designed financial dashboard built in Python using **Streamlit** and **Plotly**. It visualizes daily stock price trends alongside Foreign Institutional Investors' Net Buy/Sell volume over a rolling 6-month period for TAIEX and preset/custom stocks in the Taiwan market.

This project is built using a clean **Object-Oriented Design (OOD)** to separate data extraction, validation, and fallbacks (in `data_service.py`) from layout rendering and user interactions (in `app.py`).

---

## Features

1. **Clean Object-Oriented Design (OOD)**:
   - High cohesion and low coupling between modules.
   - Core data operations isolated in `data_service.py` using classes: `AssetConfig`, `DataFetcher`, `FallbackGenerator`, and `MarketDataService`.
   - Layout rendering isolated in `app.py` under the `DashboardUI` controller class.
2. **Dynamic & Custom Assets**:
   - TAIEX (Taiwan Capitalization Weighted Stock Index) is always available as the default view.
   - Support for selecting pre-configured top-weighted stocks (TSMC, Foxconn, MediaTek, Quanta Computer, Fubon Financial).
   - Support for **Custom Stock Input**: Enter any valid numerical stock code (e.g., `2303` or `2303.TW`) to retrieve custom analytics dynamically.
3. **Dual-Axis Subplots**:
   - **Top Subplot**: Interactive price charts supporting both **Candlestick** and **Line** layouts.
   - **Bottom Subplot**: Color-coded bar charts showing Foreign Institutional Investors' Net Flows (Emerald Green for net buys, Rose Red for net sells).
4. **Key Metric Indicators**: High-level KPI cards displaying the latest closing price, daily changes, daily net capital flows, and cumulative flows for the selected timeframe.
5. **Robust Caching & Rate Limiting**: Implements Streamlit `st.cache_data` (1-hour TTL) and a realistic fallback simulation layer to prevent API blocks or app crashes.
6. **Data Export**: Displays recent transaction records in an interactive table with a direct download button to export the combined datasets as CSV.

---

## File Structure

```
python_TW_Stock_Foreign_Tracker/
├── app.py             # UI rendering and controls (DashboardUI controller class)
├── data_service.py    # Business logic & APIs (AssetConfig, DataFetcher, FallbackGenerator, MarketDataService)
├── requirements.txt   # Declared python dependencies
├── README.md          # User setup and execution manual (this file)
└── documentation.md   # System architecture and technical flow documentation
```

---

## Installation & Setup

Ensure you have **Python 3.11+** installed.

### 1. Clone or Open the Workspace
Navigate to the project root directory:
```bash
cd python_TW_Stock_Foreign_Tracker
```

### 2. Set Up a Virtual Environment (Recommended)
Activate your virtual environment:
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## How to Execute

To launch the interactive dashboard locally, run:

```bash
streamlit run app.py
```

Once running, navigate to:
👉 **[http://localhost:8501](http://localhost:8501)**

### Sidebar Settings
- **Target Asset**: Select pre-configured assets or choose `"Custom Ticker..."`.
- **Custom Input**: Type any Taiwan Stock symbol (e.g. `2303` for UMC) to query it dynamically.
- **Timeframe (Start/End Date)**: Customize the date range for your analysis (defaults to the last 6 months).
- **Price Chart Style**: Toggle between **Candlestick** and **Line** layouts.
- **FinMind API Token (Optional)**: Input your FinMind API token to bypass public rate limit thresholds.