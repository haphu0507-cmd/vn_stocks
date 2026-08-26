import vnstock
v = vnstock.Vnstock()
stock = v.stock(symbol='FPT', source='VCI')

print("Inspecting stock object for ratios...")
print([m for m in dir(stock) if not m.startswith('__')])

if hasattr(stock, 'finance'):
    print("Found finance attribute. Inspecting finance...")
    print([m for m in dir(stock.finance) if not m.startswith('__')])
    
    # Try common ratios method
    if hasattr(stock.finance, 'ratio'):
        print("Found ratio method in finance. Testing...")
        # usually takes 'period' and 'lang'
        try:
            ratios = stock.finance.ratio(period='quarter', lang='vi')
            print("Ratio data fetched (quarter):")
            print(ratios.head())
        except Exception as e:
            print(f"Error fetching quarter ratios: {e}")
            
# Check for fundamental info
if hasattr(stock, 'quote'):
    print("Inspecting quote for potential ratio summary...")
    # Some libs have a basic summary
    
