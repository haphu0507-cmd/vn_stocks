from data_loader import get_stock_data
from indicators import calculate_indicators

def main():
    print("Testing data fetching for FPT...")
    df = get_stock_data('FPT', days=100)
    if df.empty:
        print("FAIL: No data fetched.")
        return

    print(f"Data fetched: {len(df)} rows.")
    print("Testing indicator calculation...")
    df_ind = calculate_indicators(df)
    
    if 'MA50' in df_ind.columns and 'RSI' in df_ind.columns:
        print("SUCCESS: Indicators calculated.")
        print(df_ind.tail())
    else:
        print("FAIL: Indicators missing.")

if __name__ == "__main__":
    main()
