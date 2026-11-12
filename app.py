import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io

st.set_page_config(page_title="Nifty 500 RS Scanner", layout="wide")
st.title("🦅 Nifty 500 - Top 20% RS Scanner")
st.write("Fetching live Nifty 500 symbols & applying Trend + RS Rules.")

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
    
    status.text("Downloading market data... (isme 1-2 minute lag sakte hain)")
    # Benchmark data (^CRSLDX BSE 500 ka ticker hai jo Nifty 500 ka perfect proxy hai)
    bench = yf.download("^CRSLDX", period="3y", interval="1wk", progress=False)
    bench_close = bench['Close'].squeeze()
    
    # Fast batch download
    data = yf.download(tickers, period="3y", interval="1wk", group_by="ticker", progress=False, threads=True)
    
    results = []
    for t in tickers:
        try:
            if t not in data.columns.levels[0]: continue
            df = data[t]
            close_price = df['Close'].dropna()
            
            if len(close_price) > 52:
                wma_20 = close_price.rolling(window=20).mean()
                wma_50 = close_price.rolling(window=50).mean()
                
                # Mansfield RS Calculation
                rs_ratio = close_price / bench_close
                rs_52_ma = rs_ratio.rolling(window=52).mean()
                mansfield_rs = ((rs_ratio / rs_52_ma) - 1) * 100
                
                latest_close = float(close_price.iloc[-1])
                latest_20wma = float(wma_20.iloc[-1])
                latest_50wma = float(wma_50.iloc[-1])
                latest_m_rs = float(mansfield_rs.iloc[-1])
                prev_20wma = float(wma_20.iloc[-2])
                
                results.append({
                    "Stock": t.replace(".NS", ""),
                    "Close": latest_close,
                    "Mansfield RS": latest_m_rs,
                    "20 WMA": latest_20wma,
                    "50 WMA": latest_50wma,
                    "Prev 20 WMA": prev_20wma
                })
        except Exception:
            pass
            
    status.text("Applying Top 20% RS and Trend Filters...")
    
    if results:
        df_all = pd.DataFrame(results)
        # Top 20% RS rule
        rs_80th = df_all['Mansfield RS'].quantile(0.8)
        
        final = df_all[
            (df_all['Mansfield RS'] >= rs_80th) & 
            (df_all['Close'] > df_all['20 WMA']) & 
            (df_all['20 WMA'] > df_all['50 WMA']) & 
            (df_all['20 WMA'] > df_all['Prev 20 WMA'])
        ]
        
        status.empty() 
        
        if not final.empty:
            st.success(f"✅ {len(final)} Stocks Found! (Top 20% RS Cutoff: {round(rs_80th, 2)})")
            display_df = final.sort_values(by="Mansfield RS", ascending=False).drop(columns=['Prev 20 WMA'])
            st.dataframe(display_df.round(2), use_container_width=True, hide_index=True)
        else:
            st.warning("Aaj koi stock saare rules pass nahi kar paya.")
