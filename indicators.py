import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators for input OHLCV dataframe.
    Indicators computed:
    - Moving Averages: SMA20, SMA50, SMA200, EMA20
    - RSI (14)
    - MACD (Line, Signal, Histogram)
    - Bollinger Bands (Upper, Middle, Lower)
    - Volume MA20 & Volume Ratio
    - Price % changes (1D, 1W, 1M)
    - Composite Trading Signal & Crossover tags
    """
    if df is None or df.empty or len(df) < 5:
        return df

    data = df.copy()
    data = data.loc[:, ~data.columns.duplicated()]
    data.columns = [c.lower() for c in data.columns]
    
    close = data['close']
    volume = data['volume'] if 'volume' in data.columns else pd.Series(index=data.index, dtype=float)

    # 1. Moving Averages
    data['MA20'] = close.rolling(window=20, min_periods=1).mean()
    data['MA50'] = close.rolling(window=50, min_periods=1).mean() if len(data) >= 50 else np.nan
    data['MA200'] = close.rolling(window=200, min_periods=1).mean() if len(data) >= 200 else np.nan
    data['EMA20'] = close.ewm(span=20, adjust=False).mean()

    # 2. RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / (loss.replace(0, np.nan))
    data['RSI'] = 100 - (100 / (1 + rs))
    data['RSI'] = data['RSI'].fillna(50)

    # 3. MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    data['MACD'] = ema12 - ema26
    data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
    data['MACD_Hist'] = data['MACD'] - data['MACD_Signal']

    # 4. Bollinger Bands (20, 2)
    std20 = close.rolling(window=20, min_periods=1).std()
    data['BB_Middle'] = data['MA20']
    data['BB_Upper'] = data['MA20'] + (std20 * 2)
    data['BB_Lower'] = data['MA20'] - (std20 * 2)

    # 5. Volume Analysis
    if not volume.empty and volume.sum() > 0:
        data['Vol_MA20'] = volume.rolling(window=20, min_periods=1).mean()
        data['Vol_Ratio'] = (volume / data['Vol_MA20']).round(2)
    else:
        data['Vol_MA20'] = np.nan
        data['Vol_Ratio'] = 1.0

    # 6. Price Performance (% changes)
    data['change_1d'] = close.pct_change(periods=1) * 100
    data['change_1w'] = close.pct_change(periods=5) * 100 if len(data) >= 5 else np.nan
    data['change_1m'] = close.pct_change(periods=20) * 100 if len(data) >= 20 else np.nan

    return data

def evaluate_signal(row: pd.Series) -> dict:
    """
    Evaluates composite technical signal and status badges for a single stock summary row.
    """
    price = row.get('close', np.nan)
    ma20 = row.get('MA20', np.nan)
    ma50 = row.get('MA50', np.nan)
    ma200 = row.get('MA200', np.nan)
    rsi = row.get('RSI', np.nan)
    macd = row.get('MACD', np.nan)
    macd_sig = row.get('MACD_Signal', np.nan)

    signal = "Trung tính"
    color = "gray"

    if pd.notna(ma50) and pd.notna(ma200):
        if price > ma20 and price > ma50 and price > ma200 and rsi > 50 and macd > macd_sig:
            signal = "Tăng mạnh"
            color = "#00c853" # Bright Green
        elif price > ma50 and price > ma200:
            signal = "Tăng giá"
            color = "#2e7d32" # Green
        elif price < ma20 and price < ma50 and price < ma200 and rsi < 40:
            signal = "Giảm mạnh"
            color = "#d50000" # Bright Red
        elif price < ma50 and price < ma200:
            signal = "Giảm giá"
            color = "#c62828" # Red
    elif pd.notna(ma50):
        if price > ma50:
            signal = "Tăng giá (>MA50)"
            color = "#2e7d32"
        elif price < ma50:
            signal = "Giảm giá (<MA50)"
            color = "#c62828"

    # Status badges
    badges = []
    if pd.notna(rsi):
        if rsi >= 70:
            badges.append("Quá mua")
        elif rsi <= 30:
            badges.append("Quá bán")

    if pd.notna(macd) and pd.notna(macd_sig):
        if macd > macd_sig:
            badges.append("MACD Mua")
        else:
            badges.append("MACD Bán")

    return {
        "Signal": signal,
        "Color": color,
        "Badges": ", ".join(badges) if badges else "Bình thường"
    }

