import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from anthropic import Anthropic
from collections import defaultdict
import json
from pathlib import Path
import os
import base64
from dotenv import load_dotenv
from datetime import datetime
import asyncio
import httpx  # Add this import
import openai
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Remove or comment out the deepseek_coder import since we'll use HTTP API
# import deepseek_coder

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')  # Add this line

claude = Anthropic(api_key=CLAUDE_API_KEY)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

AI_OPTIONS = [
    [InlineKeyboardButton("ChatGPT", callback_data="ai_chatgpt")],
    [InlineKeyboardButton("Claude", callback_data="ai_claude")],
    [InlineKeyboardButton("DeepSeek", callback_data="ai_deepseek")]  # <-- Uncommented
]

MODE_OPTIONS = [
    [InlineKeyboardButton("Translation", callback_data="mode_translation")],
    [InlineKeyboardButton("General use", callback_data="mode_general")]
]

LANG_OPTIONS = [
    [InlineKeyboardButton("Luo", callback_data="lang_luo")],
    [InlineKeyboardButton("Swahili (Kenya)", callback_data="lang_swahili")]
]

TRANSLATION_SYSTEM_PROMPTS = {
    "luo": (
        "You are a translator from Luo in Kenya. "
        "Whatever I send you in English you translate to Luo in a naturally spoken way, "
        "easy to understand even for children and completely uneducated people, using rather short sentences. "
        "And break the translation down. Whatever I send in Luo you translate to English."
    ),
    "swahili": (
        "You are a translator from Swahili in Kenya. "
        "Whatever I send you in English you translate to Swahili in a naturally spoken way, "
        "easy to understand even for children and completely uneducated people, using rather short sentences. "
        "And break the translation down. Whatever I send in Swahili you translate to English."
    )
}

async def ask_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=InlineKeyboardMarkup(MODE_OPTIONS)
    )

async def ask_ai_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Which AI would you like to use?",
        reply_markup=InlineKeyboardMarkup(AI_OPTIONS)
    )

async def ask_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Which language do you want to translate?",
        reply_markup=InlineKeyboardMarkup(LANG_OPTIONS)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await ask_mode(update, context)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Reset complete. Starting fresh.")
    await ask_mode(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("mode_"):
        mode = data.replace("mode_", "")
        context.user_data["mode"] = mode
        if mode == "translation":
            await ask_lang(query, context)
        else:
            await ask_ai_choice(query, context)
        return

    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        context.user_data["lang"] = lang
        context.user_data["system_prompt"] = TRANSLATION_SYSTEM_PROMPTS[lang]
        await ask_ai_choice(query, context)
        return

    if data.startswith("ai_"):
        ai_choice = data.replace("ai_", "")
        context.user_data["ai_choice"] = ai_choice
        await query.message.reply_text("Setup complete! Send your message.")
        return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    message_id = update.message.message_id

    # Prevent duplicate replies
    last_answered_id = context.user_data.get("last_answered_id")
    if last_answered_id == message_id:
        return  # Already answered this message

    context.user_data["last_answered_id"] = message_id

    if "ai_choice" not in context.user_data:
        await update.message.reply_text("Please restart with /start and complete setup.")
        return

    # Optionally: keep chat history for context (not for re-answering)
    chat_history = context.user_data.setdefault("chat_history", [])
    chat_history.append({"role": "user", "content": user_message})
    if len(chat_history) > 20:
        chat_history.pop(0)  # Limit history size

    system_prompt = context.user_data.get("system_prompt", "Provide direct, brief responses. Focus on key points.")
    ai_choice = context.user_data.get("ai_choice", "claude")

    if ai_choice == "deepseek":
        assistant_message = await get_deepseek_response(user_message, system_prompt)  # <-- Uncommented
    elif ai_choice == "chatgpt":
        assistant_message = await get_chatgpt_response(user_message, system_prompt)
    else:
        assistant_message = await get_claude_response(user_message, system_prompt)

    chat_history.append({"role": "assistant", "content": assistant_message})
    await update.message.reply_text(assistant_message)

async def get_claude_response(message_content: str, system_message: str) -> str:
    messages = [{"role": "user", "content": message_content}]
    response = claude.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4096,
        temperature=0.7,
        system=system_message,
        messages=messages
    )
    return response.content[0].text

async def get_deepseek_response(message_content: str, system_message: str) -> str:
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",  # Updated model name
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message_content}
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
        "stream": False
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"DeepSeek API error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response content: {e.response.text}")
        return "Sorry, there was an error with the DeepSeek API. Please try again or choose a different AI."

async def get_chatgpt_response(message_content: str, system_message: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": message_content}
        ],
        max_tokens=1024,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

async def error_handler(update, context):
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8090), HealthHandler)  # Changed from 8080 to 8090
    server.serve_forever()

def main():
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("reset", reset))
        application.add_handler(CallbackQueryHandler(handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)  # Add this line
        print("Bot started...")
        threading.Thread(target=run_health_server, daemon=True).start()
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logging.exception("Bot failed to start")
        print(f"Exception: {e}")

if __name__ == '__main__':
    main()

import deepseek_coder
print(dir(deepseek_coder))