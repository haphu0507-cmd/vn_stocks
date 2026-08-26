import vnstock
try:
    stock = vnstock.Vnstock().stock(symbol='VNM', source='TCBS')
    print("Stock object created.")
    print(dir(stock))
    
    # Try common attribute names for history
    if hasattr(stock, 'quote'):
        print("Stock.quote members:", dir(stock.quote))
        if hasattr(stock.quote, 'history'):
             print("Found history method in quote.")
except Exception as e:
    print(f"Error: {e}")
