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
    "Chứng khoán": ['SSI', 'VND', 'HCM', 'VCI', 'SHS', 'FTS', 'MBS','VIX']
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

def get_stock_intraday_price_depth(symbol: str, mysql_config: dict = None, save_to_db: bool = True) -> tuple:
    """
    Fetches intraday tick data for a symbol, aggregates trading volume at each specific price level,
    and optionally persists the result to MySQL.
    """
    symbol = symbol.upper()
    try:
        quote = Quote(symbol=symbol, source='VCI')
        df_raw = quote.intraday(page_size=5000)
        
        if df_raw is None or df_raw.empty:
            return pd.DataFrame(), pd.DataFrame()
            
        # Standardize columns
        df = df_raw.copy()
        df['time'] = pd.to_datetime(df['time'])
        df['trade_date'] = df['time'].dt.date
        
        latest_date = df['trade_date'].iloc[0]
        
        # Categorize buy/sell/other volume
        def get_match_category(val):
            s = str(val).strip().lower()
            if s in ['buy', 'mua', 'b']:
                return 'buy'
            elif s in ['sell', 'bán', 'ban', 's']:
                return 'sell'
            return 'other'

        df['cat'] = df['match_type'].apply(get_match_category)
        df['buy_vol'] = df.apply(lambda r: r['volume'] if r['cat'] == 'buy' else 0, axis=1)
        df['sell_vol'] = df.apply(lambda r: r['volume'] if r['cat'] == 'sell' else 0, axis=1)
        df['other_vol'] = df.apply(lambda r: r['volume'] if r['cat'] == 'other' else 0, axis=1)
        
        # Group by price level
        aggregated = df.groupby('price').agg(
            buy_vol=('buy_vol', 'sum'),
            sell_vol=('sell_vol', 'sum'),
            other_vol=('other_vol', 'sum'),
            total_volume=('volume', 'sum'),
            trade_count=('volume', 'count')
        ).reset_index()
        
        total_vol_session = aggregated['total_volume'].sum()
        if total_vol_session > 0:
            aggregated['ratio_pct'] = (aggregated['total_volume'] / total_vol_session) * 100
        else:
            aggregated['ratio_pct'] = 0.0
            
        aggregated = aggregated.sort_values(by='price', ascending=False).reset_index(drop=True)
        
        # Optionally save to MySQL
        if save_to_db:
            try:
                from database import save_price_depth_to_mysql
                save_price_depth_to_mysql(symbol, latest_date, aggregated, df_raw, config=mysql_config)
            except Exception as ex:
                pass
                
        return aggregated, df
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

def sync_multiple_price_depth(tickers: list, mysql_config: dict = None) -> dict:
    """Fetches and saves price depth data for multiple tickers to MySQL."""
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ticker = {
            executor.submit(get_stock_intraday_price_depth, symbol, mysql_config, True): symbol for symbol in tickers
        }
        for future in as_completed(future_to_ticker):
            symbol = future_to_ticker[future]
            try:
                agg_df, _ = future.result()
                if not agg_df.empty:
                    results[symbol] = len(agg_df)
            except Exception:
                pass
    return results

