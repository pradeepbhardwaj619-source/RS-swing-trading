import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import requests
import io

st.set_page_config(page_title="Pro Terminal Scanner", layout="wide")
st.title("🦅 RS Breakout Pro Terminal")

@st.cache_data
def get_nifty_500():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    df = pd.read_csv(io.StringIO(res.text))
    return [str(sym) + ".NS" for sym in df['Symbol'].tolist()]

if st.button("Start Fast Scan (Top 100 for Demo)"):
    status = st.empty()
    status.text("Fetching NSE symbols...")
    
    # Fast testing ke liye abhi top 100 stocks utha rahe hain. 
    # Aap isko wapas get_nifty_500() kar sakte ho baad mein.
    tickers = get_nifty_500()[:100] 
    
    status.text("Downloading data...")
    data = yf.download(tickers, period="1y", interval="1d", group_by="ticker", progress=False, threads=True)
    
    results = []
    for t in tickers:
        try:
            if t not in data.columns.levels[0]: continue
            df = data[t]
            close_prices = df['Close'].dropna()
            
            if len(close_prices) > 200:
                cmp = float(close_prices.iloc[-1])
                sma_20 = float(close_prices.rolling(window=20).mean().iloc[-1])
                sma_50 = float(close_prices.rolling(window=50).mean().iloc[-1])
                sma_200 = float(close_prices.rolling(window=200).mean().iloc[-1])
                
                ret_3m = ((cmp - float(close_prices.iloc[-63])) / float(close_prices.iloc[-63])) * 100
                
                results.append({
                    "Symbol": t.replace(".NS", ""),
                    "Close": cmp,
                    "3M_Ret": ret_3m,
                    "20_SMA": sma_20,
                    "50_SMA": sma_50,
                    "200_SMA": sma_200
                })
        except Exception:
            pass
            
    if results:
        df_all = pd.DataFrame(results)
        df_all['3M_RS'] = (df_all['3M_Ret'].rank(pct=True) * 100)
        
        # Base trend filters
        final = df_all[
            (df_all['Close'] > df_all['200_SMA']) & 
            (df_all['Close'] > df_all['20_SMA'])
        ]
        
        status.empty() 
        
        if not final.empty:
            st.success(f"✅ Scanning Complete! Select a stock below to analyze.")
            display_df = final.sort_values(by="3M_RS", ascending=False).round(2).drop(columns=['3M_Ret'])
            
            # SIDEBAR: List of passing stocks (Clickable)
            stock_list = display_df['Symbol'].tolist()
            selected_stock = st.selectbox("🎯 Select Stock to Open Dashboard:", stock_list)
            
            # TABLE SUMMARY
            with st.expander("View Full Scan Table"):
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # ==========================================
            # 🚀 PRO DASHBOARD FOR SELECTED STOCK
            # ==========================================
            st.subheader(f"📊 Live Dashboard: {selected_stock}")
            
            # Do columns banayein: Left side Chart, Right side Fundamentals
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### TradingView Live Chart")
                # TradingView ka embed code HTML ke through inject kar rahe hain
                tv_widget = f"""
                <!-- TradingView Widget BEGIN -->
                <div class="tradingview-widget-container">
                  <div id="tradingview_7e4e1"></div>
                  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                  <script type="text/javascript">
                  new TradingView.widget(
                  {{
                  "width": "100%",
                  "height": 500,
                  "symbol": "NSE:{selected_stock}",
                  "interval": "D",
                  "timezone": "Asia/Kolkata",
                  "theme": "dark",
                  "style": "1",
                  "locale": "in",
                  "enable_publishing": false,
                  "hide_top_toolbar": false,
                  "save_image": false,
                  "container_id": "tradingview_7e4e1"
                }}
                  );
                  </script>
                </div>
                <!-- TradingView Widget END -->
                """
                components.html(tv_widget, height=520)

            with col2:
                st.markdown("### Fundamental Snapshot")
                st.info("💡 Note: For deep fundamentals, TickerTape ya Screener visit karein.")
                
                # Yahoo Finance se quick fundamental data lana
                try:
                    tkr = yf.Ticker(selected_stock + ".NS")
                    info = tkr.info
                    
                    st.metric("Sector", info.get("sector", "N/A"))
                    st.metric("Industry", info.get("industry", "N/A"))
                    st.metric("Market Cap (Cr)", round(info.get("marketCap", 0) / 10000000, 2))
                    st.metric("PE Ratio", round(info.get("trailingPE", 0), 2))
                    st.metric("Div Yield %", round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else 0)
                    
                    st.markdown(f"[🔗 Open in Screener.in](https://www.screener.in/company/{selected_stock}/)")
                except Exception as e:
                    st.warning("Fundamental data fetch nahi ho paya.")

        else:
            st.warning("Aaj koi stock saare rules pass nahi kar paya.")
