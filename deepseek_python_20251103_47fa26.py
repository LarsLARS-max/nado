from telegram.ext import ApplicationBuilder

application = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .proxy_url('socks5://proxy_url:port')  # если нужен прокси
    .build()
)