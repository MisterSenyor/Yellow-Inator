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
                
            if type(groups[group]) != dict:
                keyboard.append([])
                _fill_keyboard_by_group(chat_id, keyboard[-1], groups[group], idx=idx)
            else:
                _fill_keyboard_by_group(chat_id, keyboard, groups[group], idx=idx)
    elif type(groups) == list:
        for group in groups:
            if idx:
                chat_button_states[chat_id].append(f"⚫ {group}")
                keyboard.append(InlineKeyboardButton(f"⚫ {group}", callback_data=str(len(chat_button_states[chat_id]) - 1)))
            else:
                print(len(keyboard))
                keyboard.append(InlineKeyboardButton(chat_button_states[chat_id][chat_state_idx[chat_id]], callback_data=str(chat_state_idx[chat_id])))
                print(len(keyboard))
                chat_state_idx[chat_id] += 1
    
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
            participants = db.get_users_by_groups_OR(chat_selected_buttons[chat_id])
            participants = sorted(participants, key=lambda x: x[1]["points"])
            participants_str = '\n'.join([x[1]['name'] for x in participants[:int(chat_input[chat_id][1])]])
            await query.edit_message_text(f"המשתתפים הם:\n{participants_str}\nעם {chat_input[chat_id][0]} נקודות לכל משתתף.")
            chat_prompt_state[chat_id] += 1
            await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
        else:
            await query.edit_message_text("No options selected.")
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

async def handle_swap_button(update, context: ContextTypes.DEFAULT_TYPE):
    global participants, chat_button_states
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        participants_str = "\n".join([x[1]['name'] for x in participants[:int(chat_input[chat_id][1])]])
        await query.edit_message_text(f"המשתתפים הם:\n{participants_str}\nעם {chat_input[chat_id][0]} נקודות לכל משתתף.")
        users_update = {name: {"points": vals["points"] + chat_input[chat_id][0]} for name, vals in participants[:int(chat_input[chat_id][1])]}
        db.update_users_db(users_update)
        reset_handlers_to_default(chat_id)
        chat_prompt_state[chat_id] += 1
    else:
        idx = int(query.data)
        if idx < len(chat_button_states[chat_id]):
            participants.pop(idx)
            
            chosen_users = [x[1]['name'] for x in participants[:int(chat_input[chat_id][1])]]
            keyboard = []
            for idx, user in enumerate(chosen_users):
                keyboard.append([InlineKeyboardButton(f"{user}", callback_data=idx)])
            keyboard.append([InlineKeyboardButton("סיימתי", callback_data='submit')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text('סמן אנשים שתרצה להחליף:', reply_markup=reply_markup) 

async def handle_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_input, chat_prompt_state
    chat_id = update.message.chat_id
    try:
        number = int(update.message.text)  # Ensure the input is a valid number
        chat_input[chat_id].append(number)  # Store the input number
        # Delete the prompt message
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
        
        chat_prompt_state[chat_id] += 1
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
        
    except ValueError:
        await update.message.reply_text("הוזן קלט לא תקין. נסה שוב:")

async def button_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_button_states
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    await points_prompts[chat_prompt_state[chat_id]]["func"](update, context)
    

points_prompts = [{"prompt": init_text_prompt_func_generator("כמה נקודות תורנות שווה המשימה?", _prompt_init_func), "func": None},
                {"prompt": text_prompt_func_generator("כמה תורנים צריך?"), "func": None},
                {"prompt": button_prompt_func_generator('קבוצות מהן לבחור משתתפים:', select_groups_prompt), "func": handle_group_button},
                {"prompt": button_prompt_func_generator('סמן אנשים שתרצה להחליף:', select_participants_prompt), "func": handle_swap_button}]

INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "points"
COMMAND_DESCRIPTION = "יצירת רשימת תורנים"
ROLES = {"קלפ"}