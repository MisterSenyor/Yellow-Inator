from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import points
import user_statistics
import exchange
import signup
import load_users
# import alert
import add_test
import report_test
from api import APP, DEFAULT_BUTTON_HANDLER, DEFAULT_FILE_HANDLER, DEFAULT_INPUT_HANDLER


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'hello {update.effective_user.first_name}')

async def set_menu(app):
    await APP.bot.set_my_commands(menu)
    
menu = []

commands = {
    points.COMMAND_NAME: {
        "initial": points.points_prompts[0]["prompt"],
        "description": points.COMMAND_DESCRIPTION
    },
    exchange.COMMAND_NAME: {
        "initial": exchange.points_prompts[0]["prompt"],
        "description": exchange.COMMAND_DESCRIPTION
    },
    signup.COMMAND_NAME: {
        "initial": signup.points_prompts[0]["prompt"],
        "description": signup.COMMAND_DESCRIPTION
    },
    load_users.COMMAND_NAME: {
        "initial": load_users.points_prompts[0]["prompt"],
        "description": load_users.COMMAND_DESCRIPTION
    },
    user_statistics.COMMAND_NAME: {
        "initial": user_statistics.points_prompts[0]["prompt"],
        "description": user_statistics.COMMAND_DESCRIPTION
    },
    # alert.COMMAND_NAME: {
        # "initial": alert.alert_prompts[0]["prompt"],
        # "description": alert.COMMAND_DESCRIPTION
    # },
    add_test.COMMAND_NAME: {
        "initial": add_test.points_prompts[0]["prompt"],
        "description": add_test.COMMAND_DESCRIPTION
    },
    report_test.COMMAND_NAME: {
        "initial": report_test.points_prompts[0]["prompt"],
        "description": report_test.COMMAND_DESCRIPTION
    }
}

def main():
    APP.add_handler(CommandHandler("hello", hello))
    APP.add_handler(DEFAULT_BUTTON_HANDLER)
    APP.add_handler(DEFAULT_INPUT_HANDLER)
    APP.add_handler(DEFAULT_FILE_HANDLER)
    for command, vals in commands.items():
        APP.add_handler(CommandHandler(command, vals["initial"]))
        menu.append(BotCommand(command, vals["description"]))
       
    APP.post_init = set_menu 
    
    APP.run_polling()
    
    
if __name__ == "__main__":
    main()