from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import APP, reset_handlers_to_default, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_input = {} # {"id": (5, 3, 2)}
chat_selected_buttons = {} # {"id": {2,4,6}}
state_idx = 0
participants = []

groups = db.get_groups()

def _prompt_init_func(app, chat_id) -> bool:
    chat_prompt_state[chat_id] = 0
    chat_input[chat_id] = [None, None]  # Initialize the user's number as None
    app.remove_handler(DEFAULT_INPUT_HANDLER)
    app.remove_handler(DEFAULT_BUTTON_HANDLER)
    app.add_handler(INPUT_HANDLER)  # Handle the number input
    app.add_handler(BUTTON_HANDLER)
    return True

def confirm_prompt(app, chat_id: int) -> None:
    keyboard = []
    keyboard.append([InlineKeyboardButton("בטל", callback_data="cancel")])
    keyboard.append([InlineKeyboardButton("מאשר", callback_data='submit')])
    return keyboard

def confirm_change_prompt(chat_id: int):
    return f"אתה {chat_input[chat_id]}?"

async def handle_send_button(update, context):
    global participants, button_states, state_idx
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        await query.edit_message_text(f"שלום, {chat_input[chat_id]}")
        reset_handlers_to_default([INPUT_HANDLER, BUTTON_HANDLER])
    else: # == "cancel"
        chat_prompt_state[chat_id] = 0
        chat_input[chat_id] = set()
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def handle_input(update: Update, context) -> None:
    global chat_input, chat_prompt_state
    # Manage signup
    chat_id = update.message.chat_id
    # if db.get_user_by_chat_id(chat_id) is not None:
    #     # Handle existing user
    #     return
    uid = update.message.text
    user = db.get_user_by_uid(uid)
    if user is None:
        # Handle nonexisting UID
        return
    chat_input[chat_id] = user[1]['name']
    user[1]['chat_id'] = chat_id
    db.update_users_db({user[0]: user[1]})
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


points_prompts = [{"prompt": init_text_prompt_func_generator("Enter UID:", _prompt_init_func), "func": None},
                  {"prompt": button_prompt_func_generator("Confirm", confirm_prompt, change_prompt=confirm_change_prompt), "func": handle_send_button}]

INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "signup"
