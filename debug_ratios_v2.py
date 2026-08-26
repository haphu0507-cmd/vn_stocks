import vnstock
v = vnstock.Vnstock()
stock = v.stock(symbol='FPT', source='VCI')
ratios = stock.finance.ratio(period='quarter', lang='vi')

print(f"Index level 0: {ratios.columns.get_level_values(0).unique().tolist()}")
print(f"Index level 1: {ratios.columns.get_level_values(1).unique().tolist()}")

# Look for ROE, ROA, PE, PB
cols = []
for c1, c2 in ratios.columns:
    if any(x in c2 for x in ['ROE', 'ROA', 'P/E', 'P/B', 'P/S']):
        cols.append((c1, c2))

print("Found relevant columns:")
print(cols)

if cols:
    print("Sample data for these columns:")
    print(ratios[cols].head(1))
