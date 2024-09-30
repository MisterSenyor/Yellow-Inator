from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import points
import exchange
import signup
import load_users
from api import APP, DEFAULT_BUTTON_HANDLER, DEFAULT_INPUT_HANDLER


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'hello {update.effective_user.first_name}')

commands = {
    points.COMMAND_NAME: {
        "initial": points.points_prompts[0]["prompt"],
        "input_handler": points.INPUT_HANDLER,
        "button_handler": points.BUTTON_HANDLER,
    },
    exchange.COMMAND_NAME: {
        "initial": exchange.points_prompts[0]["prompt"],
        "input_handler": exchange.INPUT_HANDLER,
        "button_handler": exchange.BUTTON_HANDLER,
    },
    signup.COMMAND_NAME: {
        "initial": signup.points_prompts[0]["prompt"],
        "input_handler": signup.INPUT_HANDLER,
        "button_handler": signup.BUTTON_HANDLER,
    },
    load_users.COMMAND_NAME: {
        "initial": load_users.points_prompts[0]["prompt"],
        "input_handler": load_users.INPUT_HANDLER,
        "button_handler": load_users.BUTTON_HANDLER,
        "button_handler": load_users.BUTTON_HANDLER,
    }
}

def main():
    APP.add_handler(CommandHandler("hello", hello))
    APP.add_handler(DEFAULT_BUTTON_HANDLER)
    APP.add_handler(DEFAULT_INPUT_HANDLER)
    for command, vals in commands.items():
        APP.add_handler(CommandHandler(command, vals["initial"]))
    
    APP.run_polling()
    
    
if __name__ == "__main__":
    main()