import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI
from google import genai

# =========================
# CONFIG
# =========================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

WEBHOOK_URL = os.environ["WEBHOOK_URL"]

# =========================
# CLIENTS
# =========================

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI()

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()


# =========================
# GPT
# =========================

async def ask_gpt(text: str) -> str:
    response = await openai_client.responses.create(
        model="gpt-5-mini",
        instructions=(
            "Bạn là ChatGPT trong một group Telegram. "
            "Nói chuyện tự nhiên bằng tiếng Việt, thân thiện, ngắn gọn. "
            "Dùng cách xưng hô 't' và 'm'. "
            "Có thể pha chút hài hước nhưng vẫn phải trả lời chính xác."
        ),
        input=text
    )

    return response.output_text


# =========================
# GEMINI
# =========================

async def ask_gemini(text: str) -> str:
    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model="gemini-2.5-flash",
        contents=(
            "Bạn đang nói chuyện trong group Telegram với người dùng Việt Nam. "
            "Nói chuyện tự nhiên, thân thiện, xưng hô 't' và 'm'. "
            "Trả lời ngắn gọn nhưng hữu ích.\n\n"
            f"Người dùng: {text}"
        )
    )

    return response.text


# =========================
# COMMANDS
# =========================

async def gpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text(
            "Dùng kiểu: /gpt câu hỏi của m"
        )
        return

    try:
        answer = await ask_gpt(text)
        await update.message.reply_text("🧠 GPT:\n" + answer)

    except Exception as e:
        print("GPT ERROR:", e)
        await update.message.reply_text(
            "GPT bị lỗi rồi 💀"
        )


async def gemini_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text(
            "Dùng kiểu: /gemini câu hỏi của m"
        )
        return

    try:
        answer = await ask_gemini(text)
        await update.message.reply_text("♊ Gemini:\n" + answer)

    except Exception as e:
        print("GEMINI ERROR:", e)
        await update.message.reply_text(
            "Gemini bị lỗi rồi 💀"
        )


# =========================
# NORMAL MESSAGES
# =========================

async def normal_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    if not text:
        return

    # Chỉ phản hồi khi có @mention bot
    bot_username = context.bot.username

    if bot_username and f"@{bot_username.lower()}" not in text.lower():
        return

    text = text.replace(
        f"@{bot_username}",
        ""
    ).strip()

    if not text:
        return

    try:
        answer = await ask_gpt(text)
        await update.message.reply_text(
            "🧠 GPT:\n" + answer
        )

    except Exception as e:
        print("MESSAGE ERROR:", e)


# =========================
# TELEGRAM HANDLERS
# =========================

telegram_app.add_handler(
    CommandHandler("gpt", gpt_command)
)

telegram_app.add_handler(
    CommandHandler("gemini", gemini_command)
)

telegram_app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        normal_message
    )
)


# =========================
# WEBHOOK
# =========================

@app.on_event("startup")
async def startup():

    await telegram_app.initialize()
    await telegram_app.start()

    await telegram_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/telegram"
    )


@app.on_event("shutdown")
async def shutdown():

    await telegram_app.stop()
    await telegram_app.shutdown()


@app.post("/telegram")
async def telegram_webhook(request: Request):

    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {"ok": True}


@app.get("/")
async def home():

    return {
        "status": "Tele-GemiPT is running 🤖"
    }
