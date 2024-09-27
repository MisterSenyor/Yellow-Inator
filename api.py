from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters


APP = ApplicationBuilder().token("7899662823:AAHg34XX6f2HedB9ONi_XArgTCgE4hv6q5E").build()

def text_prompt_func_generator(prompt: str) -> None:
    async def prompt_func(update: Update, context) -> None:
        global chat_prompt_state, chat_selections
        chat_id = update.message.chat_id
        print(f"{chat_id=}")
        message = await update.message.reply_text(prompt)
        context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
    return prompt_func

def init_text_prompt_func_generator(prompt: str, init_func) -> None:
    async def prompt_func(update: Update, context) -> None:
        global chat_prompt_state, chat_selections
        chat_id = update.message.chat_id
        print(f"{chat_id=}")
        init_func(APP, chat_id)
        message = await update.message.reply_text(prompt)
        context.user_data['current_command'] = update.message.text.split()[0][1:]
        context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
    return prompt_func

async def _default_input_handler(update: Update, context) -> None:
    await update.message.reply_text("Echo.")

async def _default_button_handler(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    await update.message.reply_text("Button pressed.")

DEFAULT_INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, _default_button_handler)
DEFAULT_BUTTON_HANDLER = CallbackQueryHandler(_default_input_handler)