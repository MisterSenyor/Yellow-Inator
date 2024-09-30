from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import points
import alert



async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'hello {update.effective_user.first_name}')


def main():
    app = ApplicationBuilder().token("7899662823:AAHg34XX6f2HedB9ONi_XArgTCgE4hv6q5E").build()
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("points", points.points_prompts[0]["prompt"]))
    app.add_handler(CommandHandler("first_alert", points.alert_prompts[0]["prompt"]))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, points.handle_number_input))  # Handle the number input
    app.add_handler(CallbackQueryHandler(points.button_handler))
    app.run_polling()
    
    
if __name__ == "__main__":
    main()