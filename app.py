import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io

st.set_page_config(page_title="First Breakout & RS Scanner", layout="wide")
st.title("🦅 Nifty 500 - First Breakout Scanner")
st.write("Tracking Volume Alerts & Fresh 20D Breakouts after a Pullback to avoid extended entries.")

@st.cache_data
def get_nifty_500():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    df = pd.read_csv(io.StringIO(res.text))
    return [str(sym) + ".NS" for sym in df['Symbol'].tolist()]

if st.button("Start Scan (Nifty 500)"):
    status = st.empty()
    status.text("Fetching Nifty 500 stock list from NSE...")
    tickers = get_nifty_500()
    
    status.text("Downloading daily market data... (isme 1-2 minute lag sakte hain)")
    data = yf.download(tickers, period="1y", interval="1d", group_by="ticker", progress=False, threads=True)
    
    results = []
    for t in tickers:
        try:
            if t not in data.columns.levels[0]: continue
            df = data[t]
            
            if len(df) > 200:
                cmp = float(df['Close'].iloc[-1])
                sma_20 = float(df['Close'].rolling(window=20).mean().iloc[-1])
                sma_50 = float(df['Close'].rolling(window=50).mean().iloc[-1])
                sma_200 = float(df['Close'].rolling(window=200).mean().iloc[-1])
                
                # 20D High/Low & Volume calculation (using previous day data for accuracy)
                df['Prev_20D_High'] = df['High'].shift(1).rolling(window=20).max()
                df['Prev_20D_Low'] = df['Low'].shift(1).rolling(window=20).min()
                df['Avg_Vol_20'] = df['Volume'].shift(1).rolling(window=20).mean()
                
                # Volume Alert
                latest_vol = float(df['Volume'].iloc[-1])
                avg_vol_20 = float(df['Avg_Vol_20'].iloc[-1])
                vol_alert = "🚀 High Vol" if latest_vol > (1.5 * avg_vol_20) else "-"
                
                # Logic to find the LAST 20D Low and the FIRST Breakout after that
                df['Is_Low'] = df['Low'] <= df['Prev_20D_Low']
                df['Is_High'] = df['High'] >= df['Prev_20D_High']
                
                last_60 = df.tail(60) # Scan last 3 months for the pattern
                low_days = last_60[last_60['Is_Low']]
                
                if not low_days.empty:
                    # Find the exact date it bottomed out
                    recent_low_date = low_days.index[-1]
                    subset = last_60.loc[recent_low_date:]
                    
                    # Find breakouts ONLY after it made the low
                    breakouts = subset[subset['Is_High']]
                    low_dt_str = recent_low_date.strftime("%d-%b")
                    
                    if len(breakouts) > 0:
                        bo_date = breakouts.index[0]
                        bo_price = breakouts['Prev_20D_High'].iloc[0]
                        bo_dt_str = bo_date.strftime("%d-%b")
                        bo_status = f"✅ Triggered ({bo_dt_str})"
                        diff_pct = ((cmp - bo_price) / bo_price) * 100
                    else:
                        bo_price = float(df['Prev_20D_High'].iloc[-1])
                        bo_status = "⏳ Waiting"
                        diff_pct = ((cmp - bo_price) / bo_price) * 100
                else:
                    low_dt_str = "-"
                    bo_price = float(df['Prev_20D_High'].iloc[-1])
                    bo_status = "No recent 20D Low"
                    diff_pct = ((cmp - bo_price) / bo_price) * 100
                
                # 3M Return for RS
                ret_3m = ((cmp - float(df['Close'].iloc[-63])) / float(df['Close'].iloc[-63])) * 100
                symbol_clean = t.replace(".NS", "")
                
                results.append({
                    "Stock": symbol_clean,
                    "Close": cmp,
                    "3M Return %": ret_3m,
                    "Vol Alert": vol_alert,
                    "Last 20D Low": low_dt_str,
                    "First BO Status": bo_status,
                    "BO Level": bo_price,
                    "% From Entry": diff_pct,
                    "20 SMA": sma_20,
                    "50 SMA": sma_50,
                    "200 SMA": sma_200,
                    "Chart": f"https://in.tradingview.com/chart/?symbol=NSE:{symbol_clean}",
                    "Fundamentals": f"https://www.screener.in/company/{symbol_clean}/"
                })
        except Exception:
            pass
            
    status.text("Applying Strict 200-DMA & Top 20% RS Filters...")
    
    if results:
        df_all = pd.DataFrame(results)
        df_all['3M RS'] = (df_all['3M Return %'].rank(pct=True) * 100)
        
        # Filter: Top 20% RS + Long Term Uptrend (Price > 200 SMA)
        final = df_all[
            (df_all['3M RS'] >= 80) & 
            (df_all['Close'] > df_all['200 SMA']) & 
            (df_all['Close'] > df_all['20 SMA']) & 
            (df_all['20 SMA'] > df_all['50 SMA'])
        ]
        
        status.empty() 
        
        if not final.empty:
            st.success(f"✅ {len(final)} Stocks Found! (Top 20% RS & 200-DMA Passed)")
            display_df = final.sort_values(by="3M RS", ascending=False).drop(columns=['3M Return %'])
            
            st.dataframe(
                display_df.round(2), 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Chart": st.column_config.LinkColumn("📈 Chart", display_text="Open TV"),
                    "Fundamentals": st.column_config.LinkColumn("📊 Fundamentals", display_text="Screener"),
                    "% From Entry": st.column_config.NumberColumn("% From Entry", format="%.2f %%")
                }
            )
        else:
            st.warning("Aaj koi stock saare rules pass nahi kar paya.")
