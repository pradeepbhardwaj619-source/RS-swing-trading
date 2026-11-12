import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io

st.set_page_config(page_title="Nifty 500 Daily Breakout Scanner", layout="wide")
st.title("🦅 Nifty 500 - Daily Breakout & RS Scanner")
st.write("Tracking Top 20% RS, Daily 20/50/200 SMA, 20-Day High/Low & Base Width.")

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
    
    # 1 year ka data download kar rahe hain taaki 200 days ka SMA easily nikal sake
    data = yf.download(tickers, period="1y", interval="1d", group_by="ticker", progress=False, threads=True)
    
    results = []
    for t in tickers:
        try:
            if t not in data.columns.levels[0]: continue
            df = data[t]
            close_prices = df['Close'].dropna()
            high_prices = df['High'].dropna()
            low_prices = df['Low'].dropna()
            
            # 200 DMA calculate karne ke liye kam se kam 200 din ka data zaroori hai
            if len(close_prices) > 200:
                cmp = float(close_prices.iloc[-1])
                sma_20 = float(close_prices.rolling(window=20).mean().iloc[-1])
                sma_50 = float(close_prices.rolling(window=50).mean().iloc[-1])
                sma_200 = float(close_prices.rolling(window=200).mean().iloc[-1])
                
                # 20-Day High / Low Calculation
                high_20d = float(high_prices.tail(20).max())
                low_20d = float(low_prices.tail(20).min())
                
                # Base Width aur Distance to Breakout
                base_width_pct = ((high_20d - low_20d) / low_20d) * 100 if low_20d > 0 else 0
                dist_to_breakout = ((high_20d - cmp) / cmp) * 100 if cmp > 0 else 0
                
                # 3-Month Return for RS Ranking (Approx 63 trading days)
                ret_3m = ((cmp - float(close_prices.iloc[-63])) / float(close_prices.iloc[-63])) * 100
                
                results.append({
                    "Stock": t.replace(".NS", ""),
                    "Close": cmp,
                    "3M Return %": ret_3m,
                    "20 SMA": sma_20,
                    "50 SMA": sma_50,
                    "200 SMA": sma_200,
                    "20D High": high_20d,
                    "20D Low": low_20d,
                    "Base Gap %": base_width_pct,
                    "Dist Breakout %": dist_to_breakout
                })
        except Exception:
            pass
            
    status.text("Applying Top 20% RS and Trend Filters...")
    
    if results:
        df_all = pd.DataFrame(results)
        
        # Colab wala exact Top 20% logic (3M_RS >= 80 percentile)
        df_all['3M RS'] = (df_all['3M Return %'].rank(pct=True) * 100)
        
        # FINAL FILTERS: 200 DMA + 20/50 DMA + Top 20% RS
        final = df_all[
            (df_all['3M RS'] >= 80) & 
            (df_all['Close'] > df_all['200 SMA']) & 
            (df_all['Close'] > df_all['20 SMA']) & 
            (df_all['20 SMA'] > df_all['50 SMA'])
        ]
        
        status.empty() 
        
        if not final.empty:
            st.success(f"✅ {len(final)} Stocks Found! (Strict 200-DMA & Top 20% RS Passed)")
            # Table ko clean aur sort karke dikhana
            display_df = final.sort_values(by="3M RS", ascending=False).drop(columns=['3M Return %'])
            st.dataframe(display_df.round(2), use_container_width=True, hide_index=True)
        else:
            st.warning("Aaj koi stock saare rules pass nahi kar paya.")
