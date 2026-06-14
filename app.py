import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from data_service import AssetConfig, MarketDataService

# Top-level cached function for loading and merging data
# Streamlit caching works best on standalone functions
@st.cache_data(ttl=3600, show_spinner=False)
def load_market_data(ticker_input: str, start_date_str: str, end_date_str: str, token: str = None):
    """
    Cached wrapper to load prices and institutional flows, aligning dates.
    """
    asset = AssetConfig.from_ticker(ticker_input)
    service = MarketDataService(token=token)
    df, is_mocked = service.get_merged_data(asset, start_date_str, end_date_str)
    return df, is_mocked, asset


class DashboardUI:
    """
    Controller class responsible for managing the user interface, sidebar inputs,
    rendering metrics, interactive Plotly charts, and historical listings.
    """
    def __init__(self):
        # Calculate exactly 6 months back from current date
        self.default_end_date = date.today()
        self.default_start_date = self._get_six_months_ago(self.default_end_date)
        
    def _get_six_months_ago(self, ref_date: date) -> date:
        year = ref_date.year
        month = ref_date.month
        day = ref_date.day
        
        new_month = month - 6
        new_year = year
        if new_month <= 0:
            new_month += 12
            new_year -= 1
            
        while True:
            try:
                return date(new_year, new_month, day)
            except ValueError:
                day -= 1

    def apply_custom_styles(self):
        """
        Injects CSS rules to set font properties, gradients, and KPI metrics layout.
        """
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        /* Main app typography settings */
        html, body, [data-testid="stSidebar"] {
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Gradient header layout styles */
        .main-title-container {
            padding: 1.25rem 0rem;
        }
        .main-title {
            font-weight: 700;
            font-size: 2.8rem;
            background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .main-subtitle {
            font-size: 1.1rem;
            color: #8E9CAE;
            margin-top: 0.2rem;
            margin-bottom: 1.25rem;
            font-weight: 400;
        }

        /* Customized KPI Metric Cards */
        .custom-card {
            background-color: #1E293B;
            border-radius: 16px;
            padding: 1.25rem 1.5rem;
            border: 1px solid #334155;
            box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.05);
            margin-bottom: 1rem;
        }
        .card-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.4rem;
        }
        .card-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #F8FAFC;
            line-height: 1.2;
        }
        .card-delta {
            font-size: 0.9rem;
            margin-top: 0.4rem;
            font-weight: 600;
            display: flex;
            align-items: center;
        }
        .delta-positive {
            color: #10B981;
        }
        .delta-negative {
            color: #F43F5E;
        }
        .delta-neutral {
            color: #94A3B8;
        }
        </style>
        """, unsafe_allow_html=True)

    def render_header(self):
        """
        Renders the title banner of the dashboard application.
        """
        st.markdown(
            """
            <div class="main-title-container">
                <h1 class="main-title">Taiwan Stock & Foreign Capital Dashboard</h1>
                <div class="main-subtitle">Interactive analysis of Daily Prices and Foreign Institutional Investors' Net Flows</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    def render_sidebar(self) -> tuple[str, str, str, str, str]:
        """
        Renders the dashboard sidebar navigation controls and filters.
        Returns a tuple of (resolved_ticker, start_date_str, end_date_str, chart_style, api_token).
        """
        st.sidebar.markdown("### ⚙️ Control Dashboard")
        
        # Available pre-configured options
        preset_options = [
            "TAIEX (Taiwan Weighted Index)",
            "2330.TW (TSMC)",
            "2317.TW (Foxconn)",
            "2454.TW (MediaTek)",
            "2382.TW (Quanta Computer)",
            "2881.TW (Fubon Financial)",
            "Custom Ticker..."
        ]
        
        selected_option = st.sidebar.selectbox("Target Asset", preset_options, index=0)
        
        # Resolving ticker symbol
        resolved_ticker = "^TWII"
        if selected_option == "Custom Ticker...":
            custom_input = st.sidebar.text_input(
                "Enter Ticker / Symbol (e.g., 2303, 2409.TW, ^TWII)",
                value="2303",
                help="Enter a numerical Taiwan stock code (with or without .TW) or index ticker."
            ).strip()
            resolved_ticker = custom_input if custom_input else "2330.TW"
        else:
            if "TAIEX" in selected_option:
                resolved_ticker = "^TWII"
            else:
                # Extracts ticker code from preset string: "2330.TW (TSMC)" -> "2330.TW"
                resolved_ticker = selected_option.split(" ")[0]

        # Date controls
        st.sidebar.markdown("#### Timeframe")
        start_input = st.sidebar.date_input("Start Date", self.default_start_date)
        end_input = st.sidebar.date_input("End Date", self.default_end_date)
        
        start_str = start_input.strftime("%Y-%m-%d")
        end_str = end_input.strftime("%Y-%m-%d")

        # Visualization style toggle
        chart_style = st.sidebar.radio("Price Chart Style", ["Candlestick", "Line"], index=0)

        # Optional Token
        st.sidebar.markdown("#### API settings")
        api_token = st.sidebar.text_input(
            "FinMind API Token (Optional)",
            type="password",
            help="Allows increased request limits when loading stock metrics."
        ).strip()
        
        return resolved_ticker, start_str, end_str, chart_style, api_token

    def render_kpi_cards(self, df: pd.DataFrame, asset: AssetConfig):
        """
        Renders custom styled KPI cards summarizing price and foreign capital flow metrics.
        """
        kpi_cols = st.columns(3)
        
        latest_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else latest_row
        
        latest_price = latest_row["Close"]
        prev_price = prev_row["Close"]
        price_diff = latest_price - prev_price
        price_pct = (price_diff / prev_price) * 100 if prev_price != 0 else 0
        
        # Select format representation based on Index vs Stock
        price_fmt = f"{latest_price:,.2f}" if asset.is_index else f"{latest_price:,.1f}"
        diff_fmt = f"{price_diff:+.2f}" if asset.is_index else f"{price_diff:+.1f}"
        
        price_class = "delta-positive" if price_diff >= 0 else "delta-negative"
        price_arrow = "▲" if price_diff >= 0 else "▼"
        
        latest_net = latest_row["net_display"]
        net_class = "delta-positive" if latest_net >= 0 else "delta-negative"
        net_arrow = "▲ Net Buy" if latest_net >= 0 else "▼ Net Sell"
        
        cumulative_net = df["net_display"].sum()
        cum_class = "delta-positive" if cumulative_net >= 0 else "delta-negative"
        cum_arrow = "▲ Net Accum. Buy" if cumulative_net >= 0 else "▼ Net Accum. Sell"

        with kpi_cols[0]:
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-label">Latest Closing Price</div>
                <div class="card-value">{price_fmt} <span style="font-size:0.95rem; font-weight:normal; color:#94A3B8;">{asset.price_unit}</span></div>
                <div class="card-delta {price_class}">
                    {price_arrow} {diff_fmt} ({price_pct:+.2f}%) <span style="color:#94A3B8; font-weight:normal; margin-left:6px;">vs previous day</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_cols[1]:
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-label">Foreign Capital Flow (Latest Day)</div>
                <div class="card-value">{latest_net:+,.2f} <span style="font-size:0.95rem; font-weight:normal; color:#94A3B8;">{asset.volume_unit}</span></div>
                <div class="card-delta {net_class}">
                    {net_arrow} on {latest_row["Date"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with kpi_cols[2]:
            st.markdown(f"""
            <div class="custom-card">
                <div class="card-label">Cumulative Net Flow</div>
                <div class="card-value">{cumulative_net:+,.2f} <span style="font-size:0.95rem; font-weight:normal; color:#94A3B8;">{asset.volume_unit}</span></div>
                <div class="card-delta {cum_class}">
                    {cum_arrow} across the selected period
                </div>
            </div>
            """, unsafe_allow_html=True)

    def render_plotly_charts(self, df: pd.DataFrame, asset: AssetConfig, chart_style: str):
        """
        Creates and renders dual-axis shared subplots using Plotly.
        """
        st.markdown(f"### 📊 Interactive Analysis: {asset.display_name}")
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                f"Price Movement ({asset.price_unit})",
                f"Foreign Net Buy/Sell Volume ({asset.volume_unit})"
            ),
            row_width=[0.4, 0.6]  # Subplot height proportions (bottom 40%, top 60%)
        )
        
        # Plot price component (Top Subplot)
        if chart_style == "Candlestick":
            fig.add_trace(
                go.Candlestick(
                    x=df["Date"],
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name="Stock Price",
                    increasing_line_color="#10B981", # Emerald green
                    decreasing_line_color="#F43F5E", # Rose red
                    increasing_fillcolor="rgba(16, 185, 129, 0.3)",
                    decreasing_fillcolor="rgba(244, 63, 94, 0.3)"
                ),
                row=1, col=1
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=df["Date"],
                    y=df["Close"],
                    mode="lines",
                    name="Price (Close)",
                    line=dict(color="#3B82F6", width=2.5), # Sleek styling blue
                    fill='tozeroy',
                    fillcolor='rgba(59, 130, 246, 0.05)'
                ),
                row=1, col=1
            )
            
        # Plot net flow component (Bottom Subplot)
        bar_colors = ["#10B981" if val >= 0 else "#F43F5E" for val in df["net_display"]]
        fig.add_trace(
            go.Bar(
                x=df["Date"],
                y=df["net_display"],
                marker=dict(
                    color=bar_colors,
                    line=dict(color=bar_colors, width=0.5)
                ),
                name="Net Flow",
                hovertemplate="%{x}<br>Net Flow: %{y:+.2f} " + asset.volume_unit + "<extra></extra>"
            ),
            row=2, col=1
        )
        
        # Configure layout styling
        fig.update_layout(
            height=650,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False,
            xaxis_rangeslider_visible=False,
            xaxis2_rangeslider_visible=False,
            hovermode="x unified",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit", color="#94A3B8")
        )
        
        # Axis style grids
        for r in [1, 2]:
            fig.update_xaxes(showgrid=True, gridcolor="#334155", gridwidth=0.5, zeroline=False, row=r, col=1)
            fig.update_yaxes(showgrid=True, gridcolor="#334155", gridwidth=0.5, row=r, col=1)
            
        fig.update_yaxes(zeroline=True, zerolinecolor="#475569", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)

    def render_data_table(self, df: pd.DataFrame, asset: AssetConfig, start_str: str, end_str: str):
        """
        Renders historical tabular records and provides CSV export capabilities.
        """
        st.markdown("### 📋 Recent Historical Transactions")
        
        # Create cleaned dataframe for users
        export_df = df[["Date", "Open", "High", "Low", "Close", "Volume", "buy_display", "sell_display", "net_display"]].copy()
        export_df.columns = ["Date", "Open", "High", "Low", "Close", "Market Volume", "Foreign Buy", "Foreign Sell", "Foreign Net Flow"]
        
        # Reverse list to show newest records on top
        display_df = export_df.sort_values("Date", ascending=False).copy()
        
        # Value decimal formatting configurations
        val_fmt = "{:,.2f}" if asset.is_index else "{:,.1f}"
        format_dict = {
            "Open": val_fmt, "High": val_fmt, "Low": val_fmt, "Close": val_fmt,
            "Market Volume": "{:,.0f}",
            "Foreign Buy": "{:,.2f}", "Foreign Sell": "{:,.2f}", "Foreign Net Flow": "{:+.2f}"
        }
        
        tbl_col, btn_col = st.columns([4, 1])
        with tbl_col:
            st.dataframe(
                display_df.style.format(format_dict),
                use_container_width=True,
                height=280
            )
            
        with btn_col:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = export_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Full Merged CSV",
                data=csv,
                file_name=f"{asset.finmind_id}_merged_history_{start_str}_to_{end_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.markdown(
                f"""
                <div style="background-color: #0F172A; border-radius: 8px; padding: 1rem; border: 1px dashed #334155; font-size: 0.85rem; color: #94A3B8; margin-top: 1rem;">
                    <strong>Data Summary</strong><br>
                    • Total Days: {len(df)}<br>
                    • Flow Unit: {asset.volume_unit}<br>
                    • Price Unit: {asset.price_unit}
                </div>
                """,
                unsafe_allow_html=True
            )

    def run(self):
        """
        Main runner executing components sequentially.
        """
        st.set_page_config(
            page_title="Taiwan Stock & Foreign Institutional Tracker",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        self.apply_custom_styles()
        self.render_header()
        
        # Fetch inputs from sidebar
        ticker_input, start_str, end_str, chart_style, api_token = self.render_sidebar()
        
        # Load and verify data
        with st.spinner("Fetching market data..."):
            df, is_mocked, asset = load_market_data(
                ticker_input=ticker_input,
                start_date_str=start_str,
                end_date_str=end_str,
                token=api_token if api_token else None
            )
            
            if df.empty:
                st.error(f"Failed to fetch market data. Verify symbol '{ticker_input}' or adjust date range.")
                return
                
            if is_mocked:
                st.warning("⚠️ FinMind API rate limits exceeded or service offline. Simulated Foreign Net Buy/Sell volume displayed.")
                
            # Render UI components
            self.render_kpi_cards(df, asset)
            self.render_plotly_charts(df, asset, chart_style)
            self.render_data_table(df, asset, start_str, end_str)

# Entry point of app
if __name__ == "__main__":
    ui = DashboardUI()
    ui.run()
