
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import APP, reset_handlers_to_default, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_input = {} # {"id": (5, 3, 2)}
chat_selected_buttons = {} # {"id": {2,4,6}}
button_states = []
state_idx = 0
participants = []

groups = db.get_groups()

def _prompt_init_func(app, chat_id, chat_handlers) -> bool:
    if db.get_user_by_chat_id(chat_id) is None:
        return False
    chat_prompt_state[chat_id] = 0
    chat_input[chat_id] = [None, None]  # Initialize the user's number as None
    app.remove_handler(DEFAULT_INPUT_HANDLER)
    app.remove_handler(DEFAULT_BUTTON_HANDLER)
    app.add_handler(INPUT_HANDLER)  # Handle the number input
    app.add_handler(BUTTON_HANDLER)
    return True

def send_prompt(app, chat_id: int) -> None:
    keyboard = []
    keyboard.append([InlineKeyboardButton("בטל", callback_data="cancel")])
    keyboard.append([InlineKeyboardButton("העבר נקודות", callback_data='submit')])
    return keyboard

def send_change_prompt(chat_id: int):
    return f"מאשר שליחת {chat_input[chat_id][1]} נקודות תורנות אל {chat_input[chat_id][0]}?"

async def handle_send_button(update, context):
    global participants, button_states, state_idx
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        await query.edit_message_text(f"נשלחו {chat_input[chat_id][1]} נקודות תורנות אל {chat_input[chat_id][0]}.")
        target = db.get_users_by_groups([chat_input[chat_id][0]])[0]
        user = db.get_user_by_chat_id(chat_id)
        db.update_users_db({
            user[0]: {"points": user[1]["points"] - int(chat_input[chat_id][1])},
            target[0]: {"points": target[1]["points"] + int(chat_input[chat_id][1])},
        })
        reset_handlers_to_default([INPUT_HANDLER, BUTTON_HANDLER])
    else: # == "cancel"
        chat_prompt_state[chat_id] = 0
        chat_input[chat_id] = set()
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def handle_input(update: Update, context) -> None:
    global chat_input, chat_prompt_state
    chat_id = update.message.chat_id
    chat_input[chat_id][chat_prompt_state[chat_id]] = update.message.text  # Store the input
    prompt = None
    if chat_prompt_state[chat_id] == 0:
        if len(db.get_users_by_groups([update.message.text])) < 1: #unknown name
            prompt = "שם לא מזוהה. נסה שוב:"
    elif chat_prompt_state[chat_id] == 1:
        try:
            points_to_send = int(chat_input[chat_id][1].replace("-", "!"))
            if db.get_user_by_chat_id(chat_id)[1]["points"] < points_to_send: # if cannot transfer
                prompt = "אין לך מספיק נקודות תורנות להעברה הזו. נסה שוב:"
        except ValueError:
            prompt = "הוזן קלט לא תקין. אנא נסה שוב להזין מספר:"
    if prompt is not None:
        if update.message is None:
            message = await update.callback_query.edit_message_text(prompt)
            print(f"MESSAGE = {message}")
            context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
        else:
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
            message = await update.message.reply_text(prompt)
            context.user_data['message_id'] = message.message_id
        prompt = None
    else:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
        chat_prompt_state[chat_id] += 1
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def button_handler_func(update: Update, context) -> None:
    global button_states, state_idx
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    global button_states, state_idx
    chat_id = query.message.chat_id
    await points_prompts[chat_prompt_state[chat_id]]["func"](update, context)


points_prompts = [{"prompt": init_text_prompt_func_generator("למי לשלוח?", _prompt_init_func), "func": None},
                {"prompt": text_prompt_func_generator("כמה נקודות להעביר?"), "func": None},
                {"prompt": button_prompt_func_generator("מאשר?", send_prompt, change_prompt=send_change_prompt), "func": handle_send_button}]

INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "exchange"
