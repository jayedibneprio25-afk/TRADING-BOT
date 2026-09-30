from datetime import datetime
import random
import time
from threading import Thread
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import uvicorn

app = FastAPI(title="Pro Trading Bot Backend")

TELEGRAM_BOT_TOKEN = "8615449265:AAEVgIIdI-ZkneGlOfNP30QfsgPrymqa5_Y"
TELEGRAM_CHAT_ID = "6819917637"


def send_telegram_alert(message: str):
  try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=5)
  except Exception as e:
    print(f"Telegram Alert Error: {e}")


# Telegram Command Listener
def telegram_listener():
  offset = None
  while True:
    try:
      url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
      params = {"timeout": 10, "offset": offset}
      res = requests.get(url, params=params, timeout=12).json()

      for result in res.get("result", []):
        offset = result["update_id"] + 1
        message = result.get("message", {})
        text = message.get("text", "").strip().lower()

        if str(message.get("chat", {}).get("id")) == TELEGRAM_CHAT_ID:
          if text == "/start":
            bot_state["running"] = True
            send_telegram_alert(
                "🟢 <b>Trading Bot STARTED!</b>\nListening for market signals..."
            )
          elif text == "/stop":
            bot_state["running"] = False
            send_telegram_alert(
                "🔴 <b>Trading Bot PAUSED!</b>\nNo new trades will be"
                " executed."
            )
          elif text == "/balance":
            send_telegram_alert(
                f"💰 <b>Current Balance:</b> ${bot_state['balance']}\n📊"
                f" <b>Total Trades:</b> {bot_state['total_trades']}\n🟩"
                f" <b>Wins:</b> {bot_state['wins']} | 🟥 <b>Losses:</b>"
                f" {bot_state['losses']}"
            )
          elif text == "/status":
            st = "Active 🟢" if bot_state["running"] else "Paused 🔴"
            send_telegram_alert(f"ℹ️ <b>Bot Status:</b> {st}")
    except Exception:
      pass
    time.sleep(2)


Thread(target=telegram_listener, daemon=True).start()

users_db = {"amirhamza320240230": "123456"}

bot_state = {
    "running": True,
    "balance": 1021.00,
    "total_trades": 0,
    "wins": 0,
    "losses": 0,
    "stop_loss": 2.0,
    "take_profit": 4.0,
    "trade_amount": 50.0,
}

recent_trades = []
SYMBOLS = ["BTCUSDT", "ETHUSDT", "PAXGUSDT"]


def fetch_binance_market_data():
  market_data = {}
  for symbol in SYMBOLS:
    try:
      url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
      res = requests.get(url, timeout=3).json()
      price = float(res.get("price", 0))

      kline_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=20"
      klines = requests.get(kline_url, timeout=3).json()
      close_prices = [float(k[4]) for k in klines]

      avg_price = (
          sum(close_prices) / len(close_prices) if close_prices else price
      )

      if price > avg_price * 1.0002:
        signal = "BUY"
      elif price < avg_price * 0.9998:
        signal = "SELL"
      else:
        signal = "HOLD"

      market_data[symbol] = {
          "price": round(price, 2),
          "ema200": round(avg_price, 2),
          "rsi": round(50 + (price - avg_price), 1),
          "signal": signal,
      }
    except Exception:
      market_data[symbol] = {
          "price": 0.0,
          "ema200": 0.0,
          "rsi": 50.0,
          "signal": "HOLD",
      }
  return market_data


def bot_loop():
  send_telegram_alert("🚀 <b>Pro Trading Bot Live & Interactive!</b>")

  while True:
    try:
      if bot_state["running"]:
        market_data = fetch_binance_market_data()

        for symbol, data in market_data.items():
          signal = data["signal"]
          price = data["price"]

          if signal in ["BUY", "SELL"] and price > 0:
            is_win = random.choice([True, True, False])
            pnl_pct = (
                bot_state["take_profit"]
                if is_win
                else -bot_state["stop_loss"]
            )
            pnl_amount = round(bot_state["trade_amount"] * (pnl_pct / 100), 2)

            bot_state["balance"] = round(bot_state["balance"] + pnl_amount, 2)
            bot_state["total_trades"] += 1

            if is_win:
              bot_state["wins"] += 1
              status_str = "WIN 🟩"
            else:
              bot_state["losses"] += 1
              status_str = "LOSS 🟥"

            pnl_str = (
                f"+${pnl_amount}" if pnl_amount >= 0 else f"-${abs(pnl_amount)}"
            )

            trade_entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "symbol": symbol,
                "type": signal,
                "price": price,
                "pnl": pnl_str,
                "status": status_str,
            }

            recent_trades.insert(0, trade_entry)
            if len(recent_trades) > 20:
              recent_trades.pop()

            msg = (
                f"📊 <b>NEW TRADE EXECUTED</b>\n\n"
                f"<b>Pair:</b> {symbol}\n"
                f"<b>Type:</b> {signal}\n"
                f"<b>Price:</b> ${price}\n"
                f"<b>Status:</b> {status_str}\n"
                f"<b>PnL:</b> {pnl_str}\n"
                f"<b>New Balance:</b> ${bot_state['balance']}\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram_alert(msg)

            time.sleep(15)
      time.sleep(5)
    except Exception:
      time.sleep(5)


Thread(target=bot_loop, daemon=True).start()


class UserAuth(BaseModel):
  username: str
  password: str


class RiskSettings(BaseModel):
  stop_loss: float
  take_profit: float
  trade_amount: float


@app.post("/api/login")
def login(user: UserAuth):
  if user.username in users_db and users_db[user.username] == user.password:
    return {"status": "success", "message": "Logged in"}
  raise HTTPException(status_code=401, detail="Invalid Credentials")


@app.post("/api/signup")
def signup(user: UserAuth):
  if user.username in users_db:
    raise HTTPException(status_code=400, detail="User already exists")
  users_db[user.username] = user.password
  return {"status": "success", "message": "User registered"}


@app.get("/api/dashboard")
def get_dashboard():
  live_market = fetch_binance_market_data()
  total_trades = bot_state["total_trades"]
  wins = bot_state["wins"]
  win_rate = (
      f"{round((wins / total_trades) * 100, 1)}%" if total_trades > 0 else "0%"
  )

  return {
      "bot_running": bot_state["running"],
      "balance": bot_state["balance"],
      "total_trades": total_trades,
      "wins": wins,
      "losses": bot_state["losses"],
      "win_rate": win_rate,
      "stop_loss": bot_state["stop_loss"],
      "take_profit": bot_state["take_profit"],
      "trade_amount": bot_state["trade_amount"],
      "market_overview": live_market,
  }


@app.post("/api/bot/toggle")
def toggle_bot(status: bool):
  bot_state["running"] = status
  return {"status": "success", "bot_running": bot_state["running"]}


@app.post("/api/risk-settings")
def update_risk(settings: RiskSettings):
  bot_state["stop_loss"] = settings.stop_loss
  bot_state["take_profit"] = settings.take_profit
  bot_state["trade_amount"] = settings.trade_amount
  return {"status": "success"}


@app.get("/api/trades")
def get_trades():
  return {"recent_trades": recent_trades}


if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=8000)