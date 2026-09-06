import pandas as pd
from vnstock import Quote

print("--- Testing Quote VCI Intraday ---")
try:
    q_vci = Quote(symbol='FPT', source='VCI')
    df_vci = q_vci.intraday(page_size=5000)
    print("VCI intraday columns:", df_vci.columns if df_vci is not None else "None")
    if df_vci is not None and not df_vci.empty:
        print(df_vci.head())
        print("Total trades:", len(df_vci))
except Exception as e:
    print("VCI Intraday Error:", e)

print("\n--- Testing Quote DNSE Intraday / Price Depth ---")
try:
    q_dnse = Quote(symbol='FPT', source='DNSE')
    df_dnse = q_dnse.intraday(page_size=5000)
    print("DNSE intraday columns:", df_dnse.columns if df_dnse is not None else "None")
    if df_dnse is not None and not df_dnse.empty:
        print(df_dnse.head())
except Exception as e:
    print("DNSE Intraday Error:", e)

print("\n--- Testing Quote TCBS / TCBS Intraday if available ---")
try:
    for src in ['TCBS', 'KBS', 'MSN']:
        try:
            q = Quote(symbol='FPT', source=src)
            print(f"{src} methods:", [m for m in dir(q) if not m.startswith('_')])
            df = q.intraday()
            print(f"{src} intraday head:", df.head() if df is not None else "None")
        except Exception as ex:
            print(f"{src} failed:", ex)
except Exception as e:
    print("Other source error:", e)
