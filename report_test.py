from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import APP, INIT_AUTH_ENUM, init_button_prompt_func_generator, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER, reset_handlers_to_default

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_input = {} # {"id": (5, 3, 2)}
chat_selected_button = {} # {"id": {2,4,6}}
chat_button_states = {}
chat_state_idx = {}
participants = []


groups = db.get_groups()

def _prompt_init_func(app, chat_id, chat_handlers):
    if (user := db.get_user_by_chat_id(chat_id)) is None:
        return INIT_AUTH_ENUM["NOT_SIGNED_IN"]
    if type(ROLES) == set and list(set(user[1]["roles"]) & ROLES) == [] and not ("ADMIN" in user[1]["roles"]):
        return INIT_AUTH_ENUM["NO_PERMISSION"]
    chat_prompt_state[chat_id] = 0
    chat_input[chat_id] = []  # Initialize the user's number as None
    chat_button_states[chat_id] = []
    chat_handlers[chat_id]["input"] = handle_number_input
    chat_handlers[chat_id]["button"] = button_handler_func
    return None
    
def select_groups_prompt(app, chat_id: int) -> None:
    chat_selected_button[chat_id] = set()
    keyboard = []
    user = db.get_user_by_chat_id(chat_id)
    for test in db.get_tests_by_groups_OR([user[1]["battalion"], user[1]["company"]]):
        if "tests" in user[1] and test[0] in user[1]["tests"]:
            keyboard.append([InlineKeyboardButton(f'{test[0]} ({user[1]["tests"][test[0]]})', callback_data=test[0])])
        else:
            keyboard.append([InlineKeyboardButton(test[0], callback_data=test[0])])
    return keyboard

async def handle_group_button(update, context: ContextTypes.DEFAULT_TYPE):
    global participants, chat_button_states
    query = update.callback_query
    chat_id = query.message.chat_id
    
    chat_selected_button[chat_id] = query.data
    
    chat_prompt_state[chat_id] += 1
    await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def handle_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_input, chat_prompt_state
    chat_id = update.message.chat_id
    try:
        number = int(update.message.text)  # Ensure the input is a valid number
        user = db.get_user_by_chat_id(chat_id)
        if not ("tests" in user[1]):
            user[1]["tests"] = {}
        user[1]["tests"][chat_selected_button[chat_id]] = number
        db.update_users_db({user[0]: {"tests": user[1]["tests"]}})
        # Delete the prompt message
        # await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
        await update.message.reply_text("התוצאה נרשמה.")
        reset_handlers_to_default(chat_id)
        
    except ValueError:
        await update.message.reply_text("הוזן קלט לא תקין. נסה שוב:")

async def button_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_button_states
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    await points_prompts[chat_prompt_state[chat_id]]["func"](update, context)
    

points_prompts = [{"prompt": init_button_prompt_func_generator('אנא בחר מבחן:', select_groups_prompt, _prompt_init_func), "func": handle_group_button},
                {"prompt": text_prompt_func_generator("אנא הזן ציון:"), "func": None}]

INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "report_grade"
COMMAND_DESCRIPTION = "הזנת ציונים"
ROLES = {}