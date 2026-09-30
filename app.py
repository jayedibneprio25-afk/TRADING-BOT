import time
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Pro Trading Bot SaaS", page_icon="🤖", layout="wide"
)

# Dark Theme styling fixes (TradingView Dark Theme Color: #131722)
st.markdown(
    """
    <style>
    /* Force main background to TradingView dark */
    .stApp {
        background-color: #131722 !important;
        color: #ffffff !important;
    }
    /* Metric boxes styling */
    div[data-testid="stMetric"] {
        background-color: #1e222d !important;
        padding: 15px !important;
        border-radius: 8px !important;
        border: 1px solid #2a2e39 !important;
    }
    div[data-testid="stMetricLabel"] > label {
        color: #787b86 !important;
    }
    div[data-testid="stMetricValue"] > div {
        color: #d1d4dc !important;
    }
    /* General text fixes */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #d1d4dc !important;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: bold;
        background-color: #2962ff;
        color: #ffffff;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1e53e5;
        color: #ffffff;
    }
    </style>
""",
    unsafe_allow_html=True,
)

API_BASE = "http://localhost:8000/api"

if "authenticated" not in st.session_state:
  st.session_state.authenticated = False
if "username" not in st.session_state:
  st.session_state.username = ""


def render_auth_page():
  st.title("🔐 Pro Trading Bot Platform")
  tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])

  with tab1:
    st.subheader("Login to your Account")
    login_user = st.text_input("Username", key="login_user")
    login_pass = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login", use_container_width=True):
      if login_user and login_pass:
        try:
          res = requests.post(
              f"{API_BASE}/login",
              json={"username": login_user, "password": login_pass},
          )
          if res.status_code == 200:
            st.session_state.authenticated = True
            st.session_state.username = login_user
            st.success("Login Successful!")
            st.rerun()
          else:
            st.error("Invalid username or password.")
        except Exception:
          st.error("Backend Server is not running! Start bot.py first.")
      else:
        st.warning("Please fill in all fields.")

  with tab2:
    st.subheader("Create New Account")
    signup_user = st.text_input("Choose Username", key="signup_user")
    signup_pass = st.text_input(
        "Choose Password", type="password", key="signup_pass"
    )

    if st.button("Sign Up", use_container_width=True):
      if signup_user and signup_pass:
        try:
          res = requests.post(
              f"{API_BASE}/signup",
              json={"username": signup_user, "password": signup_pass},
          )
          if res.status_code == 200:
            st.success("Account created successfully! Please login.")
          else:
            st.error(res.json().get("detail", "Signup failed."))
        except Exception:
          st.error("Backend Server is not running! Start bot.py first.")
      else:
        st.warning("Please fill in all fields.")


def render_dashboard():
  head_col1, head_col2 = st.columns([4, 1])
  with head_col1:
    st.title("🤖 Pro Trading Bot Dashboard")
    st.caption(f"Logged in as: **{st.session_state.username}**")
  with head_col2:
    st.write("")
    if st.button("🚪 Logout"):
      st.session_state.authenticated = False
      st.session_state.username = ""
      st.rerun()

  try:
    dash_res = requests.get(f"{API_BASE}/dashboard").json()
    trades_res = requests.get(f"{API_BASE}/trades").json()
  except Exception:
    st.error("Failed to connect to API server.")
    st.stop()

  bot_running = dash_res.get("bot_running", True)

  # Control & Risk Management Section
  st.subheader("⚙️ Control Panel & Risk Management")
  ctrl_col1, ctrl_col2 = st.columns([1, 2])

  with ctrl_col1:
    status_text = (
        "🟢 **BOT IS ACTIVE**" if bot_running else "🔴 **BOT IS STOPPED**"
    )
    st.markdown(f"Status: {status_text}")
    btn_label = "Stop Bot ⏹️" if bot_running else "Start Bot ▶"
    if st.button(btn_label, use_container_width=True):
      requests.post(
          f"{API_BASE}/bot/toggle", params={"status": not bot_running}
      )
      st.rerun()

  with ctrl_col2:
    with st.expander("🛡 Customize Risk & Money Management"):
      with st.form("risk_form"):
        r_col1, r_col2, r_col3 = st.columns(3)
        sl_input = r_col1.number_input(
            "Stop Loss (%)",
            value=float(dash_res.get("stop_loss", 2.0)),
            min_value=0.5,
            max_value=20.0,
            step=0.5,
        )
        tp_input = r_col2.number_input(
            "Take Profit (%)",
            value=float(dash_res.get("take_profit", 4.0)),
            min_value=1.0,
            max_value=50.0,
            step=0.5,
        )
        amt_input = r_col3.number_input(
            "Trade Amount ($)",
            value=float(dash_res.get("trade_amount", 50.0)),
            min_value=10.0,
            max_value=1000.0,
            step=10.0,
        )

        submit_risk = st.form_submit_button("Save Risk Settings")
        if submit_risk:
          requests.post(
              f"{API_BASE}/risk-settings",
              json={
                  "stop_loss": sl_input,
                  "take_profit": tp_input,
                  "trade_amount": amt_input,
              },
          )
          st.success("Risk Settings Saved Successfully!")
          st.rerun()

  st.divider()

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Account Balance", f"${dash_res.get('balance', 0):,.2f}")
  m2.metric("Total Trades", dash_res.get("total_trades", 0))
  m3.metric("Win Rate", dash_res.get("win_rate", "0%"))
  m4.metric(
      "Wins / Losses",
      f"{dash_res.get('wins', 0)} / {dash_res.get('losses', 0)}",
  )

  st.divider()

  st.subheader("📡 Live Market Signals")
  market_data = dash_res.get("market_overview", {})
  if market_data:
    cols = st.columns(len(market_data))
    idx = 0
    for symbol, info in market_data.items():
      with cols[idx]:
        st.markdown(f"### {symbol}")
        st.write(f"**Price:** `${info['price']}`")
        st.write(f"**EMA200:** `${info['ema200']}`")
        st.write(f"**RSI:** `{info['rsi']}`")
        sig = info["signal"]
        if sig == "BUY":
          st.success(f"Signal: **{sig} 🟢**")
        elif sig == "SELL":
          st.error(f"Signal: **{sig} 🔴**")
        else:
          st.info(f"Signal: **{sig} ⚪**")
      idx += 1

  st.divider()

  st.subheader("📊 Live Candlestick & Performance Charts")

  # Generating dummy candles for TradingView look
  dummy_data = {
      "Date": pd.date_range(end=pd.Timestamp.now(), periods=30, freq="h"),
      "Open": [2600 + (i % 5) * 3 - (i % 3) * 2 for i in range(30)],
      "High": [2610 + (i % 5) * 4 for i in range(30)],
      "Low": [2590 - (i % 3) * 3 for i in range(30)],
      "Close": [2605 + (i % 4) * 2 - (i % 2) * 3 for i in range(30)],
  }
  df_ohlc = pd.DataFrame(dummy_data)

  fig_candle = go.Figure(
      data=[
          go.Candlestick(
              x=df_ohlc["Date"],
              open=df_ohlc["Open"],
              high=df_ohlc["High"],
              low=df_ohlc["Low"],
              close=df_ohlc["Close"],
              increasing_line_color="#089981",  # TradingView Green
              increasing_fillcolor="#089981",
              decreasing_line_color="#f23645",  # TradingView Red
              decreasing_fillcolor="#f23645",
          )
      ]
  )

  fig_candle.update_layout(
      title="ETH/USDT Interactive Candlestick Chart",
      paper_bgcolor="#131722",
      plot_bgcolor="#131722",
      font=dict(color="#d1d4dc"),
      xaxis=dict(gridcolor="#2a2e39", showgrid=True),
      yaxis=dict(gridcolor="#2a2e39", showgrid=True),
      xaxis_rangeslider_visible=False,
      height=420,
      margin=dict(l=30, r=30, t=40, b=30),
  )
  st.plotly_chart(fig_candle, use_container_width=True)

  chart_col, table_col = st.columns([1, 1])
  trades = trades_res.get("recent_trades", [])

  with chart_col:
    st.subheader("📈 Cumulative PnL Curve")
    if trades:
      df_chart = pd.DataFrame(trades)
      df_chart["pnl_num"] = (
          df_chart["pnl"].str.replace("+", "", regex=False).astype(float)
      )
      df_chart = df_chart.iloc[::-1].reset_index(drop=True)
      df_chart["cumulative_pnl"] = df_chart["pnl_num"].cumsum()

      fig_pnl = go.Figure(
          data=go.Scatter(
              y=df_chart["cumulative_pnl"],
              mode="lines+markers",
              line=dict(color="#2962ff", width=2),
              marker=dict(size=6, color="#2962ff"),
          )
      )
      fig_pnl.update_layout(
          paper_bgcolor="#131722",
          plot_bgcolor="#131722",
          font=dict(color="#d1d4dc"),
          xaxis=dict(gridcolor="#2a2e39", showgrid=True),
          yaxis=dict(gridcolor="#2a2e39", showgrid=True),
          height=320,
          margin=dict(l=20, r=20, t=20, b=20),
      )
      st.plotly_chart(fig_pnl, use_container_width=True)
    else:
      st.info("Waiting for trade PnL data...")

  with table_col:
    st.subheader("📜 Recent Trade History")
    if trades:
      st.dataframe(trades, use_container_width=True)
    else:
      st.write("No executed trades yet in this session.")


if not st.session_state.authenticated:
  render_auth_page()
else:
  render_dashboard()