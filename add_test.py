from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import APP, INIT_AUTH_ENUM, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER, reset_handlers_to_default

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_input = {} # {"id": (5, 3, 2)}
chat_selected_buttons = {} # {"id": {2,4,6}}
chat_button_states = {}
chat_state_idx = {}
participants = []



groups = db.get_groups()

def _prompt_init_func(app, chat_id, chat_handlers):
    if (user := db.get_user_by_chat_id(chat_id)) is None:
        return INIT_AUTH_ENUM["NOT_SIGNED_IN"]
    if ROLES != set() and list(set(user[1]["roles"]) & ROLES) == [] and not ("ADMIN" in user[1]["roles"]):
        return INIT_AUTH_ENUM["NO_PERMISSION"]
    chat_prompt_state[chat_id] = 0
    chat_input[chat_id] = []  # Initialize the user's number as None
    chat_button_states[chat_id] = []
    chat_handlers[chat_id]["input"] = handle_number_input
    chat_handlers[chat_id]["button"] = button_handler_func
    return None

def _fill_keyboard_by_group(chat_id, keyboard, groups, idx=False):
    if type(groups) == dict:
        for group in groups.keys():
            if idx:
                chat_button_states[chat_id].append(f"⚫ {group}")
                keyboard.append([InlineKeyboardButton(f"⚫ {group}", callback_data=str(len(chat_button_states[chat_id]) - 1))])
            else:
                keyboard.append([InlineKeyboardButton(chat_button_states[chat_id][chat_state_idx[chat_id]], callback_data=str(chat_state_idx[chat_id]))])
                chat_state_idx[chat_id] += 1
                
            if type(groups[group]) == dict:
                _fill_keyboard_by_group(chat_id, keyboard, groups[group], idx=idx)
    
def select_groups_prompt(app, chat_id: int) -> None:
    chat_selected_buttons[chat_id] = set()
    keyboard = []
    _fill_keyboard_by_group(chat_id, keyboard, groups, idx=True)
    keyboard.append([InlineKeyboardButton("סיימתי", callback_data='submit')])
    return keyboard

def select_participants_prompt(app, chat_id: int) -> None:
    chat_selected_buttons[chat_id] = set()
    keyboard = []
    chosen_users = [x[1]['name'] for x in participants[:int(chat_input[chat_id][1])]]
    for idx, user in enumerate(chosen_users):
        keyboard.append([InlineKeyboardButton(f"{user}", callback_data=idx)])
    keyboard.append([InlineKeyboardButton("סיימתי", callback_data='submit')])
    return keyboard

async def handle_group_button(update, context: ContextTypes.DEFAULT_TYPE):
    global participants, chat_button_states
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        if chat_selected_buttons[chat_id]:
            # TODO implement test adding to db
            db.update_tests_db({chat_input[chat_id][0]: chat_selected_buttons[chat_id]})
            await query.edit_message_text(f"המבחן הוזן.")
            reset_handlers_to_default(chat_id)
        else:
            await query.edit_message_text("אנא נסו מחדש, וסמנו לפחות קבוצה אחת.")
            reset_handlers_to_default(chat_id)
    else:
        # Toggle the state of the clicked option
        option = chat_button_states[chat_id][int(query.data)][2:]
        if int(query.data) < len(chat_button_states[chat_id]):
            current_text = chat_button_states[chat_id][int(query.data)]
            if "⚫" in current_text:
                chat_button_states[chat_id][int(query.data)] = f"🔵 {option}"
                chat_selected_buttons[chat_id].add(option)
            else:
                chat_button_states[chat_id][int(query.data)] = f"⚫ {option}"
                chat_selected_buttons[chat_id].discard(option)
        
        # Rebuild the keyboard with updated states
        keyboard = []
        chat_state_idx[chat_id] = 0
        _fill_keyboard_by_group(chat_id, keyboard, groups)
        keyboard.append([InlineKeyboardButton("סיימתי", callback_data='submit')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('אנא בחר את הקבוצות הרלוונטיות:', reply_markup=reply_markup)

async def handle_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_input, chat_prompt_state
    chat_id = update.message.chat_id
    chat_input[chat_id].append(update.message.text)  # Store the input number
    # Delete the prompt message
    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
    
    chat_prompt_state[chat_id] += 1
    await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def button_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_button_states
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    await points_prompts[chat_prompt_state[chat_id]]["func"](update, context)
    

points_prompts = [{"prompt": init_text_prompt_func_generator("איך לקרוא למבחן?", _prompt_init_func), "func": None},
                {"prompt": button_prompt_func_generator('קבוצות העוברות את המבחן:', select_groups_prompt), "func": handle_group_button}]

INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "add_test"
COMMAND_DESCRIPTION = "הוספת מבחן"
ROLES = {"קלפ"}