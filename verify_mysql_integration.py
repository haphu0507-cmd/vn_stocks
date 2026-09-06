import sys
import pandas as pd
from data_loader import get_stock_intraday_price_depth
from database import test_connection, init_mysql_db, get_saved_sessions_from_mysql

print("=== VERIFYING PRICE DEPTH & MYSQL MODULES ===")

# Test 1: Fetch and aggregate price depth for FPT
print("\n1. Testing Intraday Price Depth Aggregation for FPT:")
agg_df, raw_df = get_stock_intraday_price_depth('FPT', save_to_db=False)
if not agg_df.empty:
    print(f"   [SUCCESS] Aggregated {len(agg_df)} price levels for FPT.")
    print("   Sample Price Depth Data:")
    print(agg_df.head(5).to_string())
else:
    print("   [WARNING] No intraday data returned (outside trading hours or rate limited).")

# Test 2: Verify MySQL module functions exist and run smoothly
print("\n2. Testing MySQL helper functions:")
ok, msg = test_connection()
print(f"   Test Connection Output: ok={ok}, msg='{msg}'")

print("\n=== VERIFICATION FINISHED ===")
