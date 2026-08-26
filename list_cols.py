import vnstock
v = vnstock.Vnstock()
stock = v.stock(symbol='FPT', source='VCI')
ratios = stock.finance.ratio(period='quarter', lang='vi')
print("Columns in ratios dataframe:")
print(ratios.columns.tolist())
