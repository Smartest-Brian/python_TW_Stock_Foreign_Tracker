import yfinance as yf
import pandas as pd
import requests
import numpy as np
from datetime import date, datetime
from typing import Tuple, List

class AssetConfig:
    """
    Represents the configuration and metadata of a target financial asset.
    Supports index tracking (TAIEX) and stock tracking.
    """
    def __init__(self, ticker: str, finmind_id: str, is_index: bool, display_name: str, price_unit: str, volume_unit: str):
        self.ticker = ticker
        self.finmind_id = finmind_id
        self.is_index = is_index
        self.display_name = display_name
        self.price_unit = price_unit
        self.volume_unit = volume_unit

    @classmethod
    def from_ticker(cls, ticker_input: str) -> "AssetConfig":
        """
        Factory method to dynamically construct an AssetConfig from any user-input ticker.
        E.g. "2330", "2330.TW", "^TWII", or "TAIEX"
        """
        ticker_clean = ticker_input.strip().upper()
        
        # Handle index case
        if ticker_clean == "^TWII" or ticker_clean == "TAIEX":
            return cls(
                ticker="^TWII",
                finmind_id="TAIEX",
                is_index=True,
                display_name="TAIEX Index",
                price_unit="Points",
                volume_unit="NT$ Billion"
            )
        
        # Normalize stock code: "2330.TW" -> "2330", "2330" -> "2330"
        code = ticker_clean
        if "." in ticker_clean:
            code = ticker_clean.split(".")[0]
            
        if code.isdigit():
            # Standard Taiwan Stock
            yf_ticker = f"{code}.TW"
            return cls(
                ticker=yf_ticker,
                finmind_id=code,
                is_index=False,
                display_name=f"Stock {code}",
                price_unit="NT$",
                volume_unit="Million Shares"
            )
        else:
            # Fallback configuration for any unrecognized stock symbol input
            return cls(
                ticker=ticker_clean,
                finmind_id=ticker_clean,
                is_index=False,
                display_name=ticker_clean,
                price_unit="NT$",
                volume_unit="Million Shares"
            )


class DataFetcher:
    """
    Handles daily price fetches from yfinance and institutional flows from FinMind API.
    """
    @staticmethod
    def fetch_prices(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches daily prices from yfinance and cleans columns.
        """
        try:
            df = yf.download(ticker, start=start_date, end=end_date)
            if df.empty:
                return pd.DataFrame()
            
            # Remove MultiIndex level in columns if present (common in newer yfinance versions)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
                
            df = df.reset_index()
            # Convert DatetimeIndex or Timestamp to string date representation (YYYY-MM-DD)
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
            return df
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def fetch_foreign_flows(finmind_id: str, is_index: bool, start_date: str, end_date: str, token: str = None) -> pd.DataFrame:
        """
        Fetches institutional net buys/sells from FinMind API.
        """
        url = "https://api.finmindtrade.com/api/v4/data"
        dataset = "TaiwanStockTotalInstitutionalInvestors" if is_index else "TaiwanStockInstitutionalInvestorsBuySell"
        
        params = {
            "dataset": dataset,
            "start_date": start_date,
            "end_date": end_date
        }
        
        if not is_index:
            params["data_id"] = finmind_id
            
        if token:
            params["token"] = token
            
        try:
            response = requests.get(url, params=params, timeout=15)
            res_data = response.json()
            
            if res_data.get("status") == 200:
                df = pd.DataFrame(res_data.get("data", []))
                if df.empty:
                    return pd.DataFrame()
                
                # Filter specifically for Foreign Institutional Investors (Foreign_Investor)
                df_filtered = df[df["name"] == "Foreign_Investor"].copy()
                df_filtered["net_buy_sell"] = df_filtered["buy"] - df_filtered["sell"]
                return df_filtered[["date", "buy", "sell", "net_buy_sell"]]
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()


class FallbackGenerator:
    """
    Generates return-correlated simulation data when the external API rate limit is exceeded.
    """
    @staticmethod
    def generate_mock_flows(dates: List[str], prices: List[float], is_index: bool) -> pd.DataFrame:
        """
        Generates daily buy/sell volumes correlated with asset price returns.
        """
        np.random.seed(42)
        prices_arr = np.array(prices)
        returns = np.diff(prices_arr) / prices_arr[:-1]
        returns = np.insert(returns, 0, 0.0)
        
        mock_volume = []
        for ret in returns:
            # Net flow is proportional to returns plus random normal noise
            noise = np.random.normal(0, 0.01)
            val = (ret + noise) * 1e8
            mock_volume.append(val)
            
        # Scale differently for Index (NTD) vs Stock (Shares)
        scale = 100.0 if is_index else 0.01
        scaled_net = [v * scale for v in mock_volume]
        
        return pd.DataFrame({
            "date": dates,
            "buy": [abs(v) * 1.2 * scale for v in mock_volume],
            "sell": [abs(v) * 0.8 * scale if v >= 0 else abs(v) * 1.5 * scale for v in mock_volume],
            "net_buy_sell": scaled_net
        })


class MarketDataService:
    """
    Coordinator class orchestrating fetch operations, mock fallbacks, and column formatting.
    """
    def __init__(self, token: str = None):
        self.token = token

    def get_merged_data(self, asset: AssetConfig, start_date: str, end_date: str) -> Tuple[pd.DataFrame, bool]:
        """
        Fetches, aligns, and merges stock price and foreign net flows.
        Returns a tuple of (merged_df, using_mock_fallback).
        """
        prices_df = DataFetcher.fetch_prices(asset.ticker, start_date, end_date)
        if prices_df.empty:
            return pd.DataFrame(), False
            
        flows_df = DataFetcher.fetch_foreign_flows(asset.finmind_id, asset.is_index, start_date, end_date, self.token)
        
        is_mocked = False
        if flows_df.empty:
            is_mocked = True
            # Activate simulation fallback when FinMind data is missing/rate-limited
            dates = prices_df["Date"].tolist()
            prices = prices_df["Close"].tolist()
            flows_df = FallbackGenerator.generate_mock_flows(dates, prices, asset.is_index)
            
        # Aligns price dates and flow dates
        merged_df = pd.merge(prices_df, flows_df, left_on="Date", right_on="date", how="inner")
        if merged_df.empty:
            return pd.DataFrame(), False
            
        merged_df = merged_df.sort_values("Date").reset_index(drop=True)
        
        # Scale values: Index in Billions of NTD (10^9), Stocks in Millions of Shares (10^6)
        scale_factor = 1e9 if asset.is_index else 1e6
        merged_df["net_display"] = merged_df["net_buy_sell"] / scale_factor
        merged_df["buy_display"] = merged_df["buy"] / scale_factor
        merged_df["sell_display"] = merged_df["sell"] / scale_factor
        
        return merged_df, is_mocked
