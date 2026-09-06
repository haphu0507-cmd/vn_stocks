import pandas as pd
from vnstock import Quote

q = Quote(symbol='FPT', source='VCI')
df = q.intraday(page_size=5000)
if df is not None and not df.empty:
    df['time'] = pd.to_datetime(df['time'])
    df['date'] = df['time'].dt.date
    
    # Calculate Buy / Sell volumes
    df['buy_vol'] = df.apply(lambda r: r['volume'] if str(r['match_type']).lower() in ['buy', 'mua'] else 0, axis=1)
    df['sell_vol'] = df.apply(lambda r: r['volume'] if str(r['match_type']).lower() in ['sell', 'bán'] else 0, axis=1)
    df['other_vol'] = df['volume'] - df['buy_vol'] - df['sell_vol']
    
    # Group by date and price level
    price_group = df.groupby(['date', 'price']).agg(
        total_volume=('volume', 'sum'),
        buy_volume=('buy_vol', 'sum'),
        sell_volume=('sell_vol', 'sum'),
        other_volume=('other_vol', 'sum'),
        trade_count=('id', 'count')
    ).reset_index()
    
    price_group['price_vnđ'] = price_group['price'] * 1000
    price_group = price_group.sort_values(by=['date', 'price'], ascending=[False, False])
    
    print("Aggregated Price Depth Sample:")
    print(price_group.head(15))
