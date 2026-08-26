import pandas as pd
import streamlit as st
from vnstock import Quote
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Sector Presets
PRESET_GROUPS = {
    "VN30": ['ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG', 
             'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB', 
             'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE'],
    "Ngân hàng": ['ACB', 'BID', 'CTG', 'HDB', 'MBB', 'SHB', 'SSB', 'STB', 'TCB', 'TPB', 'VCB', 'VIB', 'VPB'],
    "Công nghệ & Bán lẻ": ['FPT', 'MWG', 'FRT', 'DGW', 'PET'],
    "Bất động sản": ['VHM', 'VIC', 'VRE', 'NVL', 'PDR', 'DIG', 'DXG', 'KDH', 'NLG'],
    "Thép & Vật liệu": ['HPG', 'HSG', 'NKG'],
    "Chứng khoán": ['SSI', 'VND', 'HCM', 'VCI', 'SHS', 'FTS', 'MBS']
}

def get_vn30_tickers():
    """Returns a list of VN30 tickers."""
    return PRESET_GROUPS["VN30"]

@st.cache_data(ttl=1800, show_spinner=False)
def get_stock_data(symbol: str, days: int = 1000) -> pd.DataFrame:
    """Fetches historical OHLCV data for a single symbol using vnstock Quote API."""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    try:
        quote = Quote(symbol=symbol.upper(), source='VCI')
        df = quote.history(start=start_date, end=end_date, interval='1D')
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Ensure column names are clean
        df.columns = [c.lower() for c in df.columns]
        
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df = df.sort_values('time').reset_index(drop=True)
            
        return df
    except Exception as e:
        # Silently return empty dataframe on error for smooth fallback
        return pd.DataFrame()

def get_multiple_stocks_data(tickers: list, days: int = 1000, max_workers: int = 6) -> dict:
    """Fetches stock data for multiple tickers in parallel using ThreadPoolExecutor."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(get_stock_data, symbol, days): symbol for symbol in tickers
        }
        for future in as_completed(future_to_ticker):
            symbol = future_to_ticker[future]
            try:
                data = future.result()
                if not data.empty:
                    results[symbol] = data
            except Exception:
                pass
    return results

