
# === Install dan Setup untuk Colab ===
import nest_asyncio
import asyncio
nest_asyncio.apply()

import yfinance as yf
import pandas as pd
import feedparser
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# === KONFIGURASI ===
TOKEN = "8068174016:AAH6fLA0jpu6TFHDi7rDd844okC0WCNHhLU"
PIN_CODE = "43435"
AUTHORIZED_USERS = set()
SYMBOLS = ['EURUSD=X', 'GC=F']
TIMEFRAMES = ['1m', '5m']
LOOP_DELAY = 60  # detik

# === BERITA FOREXFACTORY ===
def get_forex_news():
    try:
        rss = feedparser.parse("https://nfs.faireconomy.media/ff_calendar_thisweek.xml")
        headlines = [entry['title'] for entry in rss.entries if "USD" in entry['title']]
        return headlines[:3]
    except:
        return ["Gagal ambil berita"]

# === ANALISA TEKNIKAL DENGAN HANDLING ERROR ===
def analyze(df):
    try:
        close = df['Close']
        ema12 = EMAIndicator(close=close, window=12).ema_indicator()
        ema26 = EMAIndicator(close=close, window=26).ema_indicator()
        macd_obj = MACD(close=close)
        macd = macd_obj.macd()
        macd_signal = macd_obj.macd_signal()
        rsi = RSIIndicator(close=close).rsi()

        last = df.index[-1]
        if rsi.loc[last] < 30 and macd.loc[last] > macd_signal.loc[last] and ema12.loc[last] > ema26.loc[last]:
            return "BUY"
        elif rsi.loc[last] > 70 and macd.loc[last] < macd_signal.loc[last] and ema12.loc[last] < ema26.loc[last]:
            return "SELL"
        else:
            return None
    except Exception as e:
        return f"ANALYSIS_ERROR: {e}"

# === HANDLER TELEGRAM ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Masukkan PIN untuk mulai menerima sinyal:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if text == PIN_CODE:
        AUTHORIZED_USERS.add(chat_id)
        await update.message.reply_text("PIN benar! Anda akan mulai menerima sinyal.")
    else:
        await update.message.reply_text("PIN salah.")

async def send_signal_to_all(app, message):
    for user_id in AUTHORIZED_USERS:
        try:
            await app.bot.send_message(chat_id=user_id, text=message)
        except:
            pass

# === LOOP ANALISA ===
async def analysis_loop(app):
    while True:
        news = get_forex_news()
        news_text = "\n".join(f"- {n}" for n in news)

        for symbol in SYMBOLS:
            try:
                results = {}
                for tf in TIMEFRAMES:
                    df = yf.download(tickers=symbol, interval=tf, period='1d', progress=False)
                    df.dropna(inplace=True)
                    result = analyze(df)

                    if isinstance(result, str) and result.startswith("ANALYSIS_ERROR"):
                        print(f"{symbol} [{tf}] => {result}")
                        results[tf] = None
                    else:
                        results[tf] = result

                if results['1m'] == results['5m'] and results['1m'] is not None:
                    msg = (
                        f"**SINYAL KUAT Terdeteksi**\nPair: {symbol}\nTimeframe: M1 & M5\n"
                        f"Sinyal: {results['1m']}\nTime: {pd.Timestamp.now()}\n\nBerita Penting:\n{news_text}"
                    )
                    await send_signal_to_all(app, msg)

            except Exception as e:
                print(f"Loop error pada {symbol}: {e}")

        await asyncio.sleep(LOOP_DELAY)

# === MAIN FUNCTION ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    asyncio.create_task(analysis_loop(app))
    await app.run_polling()

# === JALANKAN BOT ===
asyncio.run(main())
