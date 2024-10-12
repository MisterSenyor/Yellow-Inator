from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import APP, INIT_AUTH_ENUM, init_button_prompt_func_generator, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER, reset_handlers_to_default

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_button_selections = {} # {id: current selections (e.g. erez -> erez, harel -> erez, harel, 22)}
chat_input = {}
chat_menu_state = {}
MENU_OPTIONS = [
    "הוסף/הורד נקודות"
]
GROUPS_CLASSES = ["battalion", "company", "team"]
GROUPS = db.get_groups()

def _prompt_init_func(app, chat_id, chat_handlers):
    if (user := db.get_user_by_chat_id(chat_id)) is None:
        return INIT_AUTH_ENUM["NOT_SIGNED_IN"]
    if ROLES != set() and list(set(user[1]["roles"]) & ROLES) == [] and not ("ADMIN" in user[1]["roles"]):
        return INIT_AUTH_ENUM["NO_PERMISSION"]
    chat_prompt_state[chat_id] = 0
    chat_handlers[chat_id]["input"] = handle_number_input
    chat_handlers[chat_id]["button"] = button_handler_func
    chat_button_selections[chat_id] = []
    chat_input[chat_id] = []
    return None

def select_group_prompt(app, chat_id: int) -> None:
    keyboard = []
    for idx, group in enumerate(GROUPS.keys()):
        keyboard.append([InlineKeyboardButton(group, callback_data=str(idx))])
    return keyboard

def select_user_prompt(app, chat_id: int) -> None:
    keyboard = []
    users = db.get_users_by_fields({GROUPS_CLASSES[i]: chat_button_selections[chat_id][i] for i in range(len(GROUPS_CLASSES))})
    for idx, user in enumerate(users):
        keyboard.append([InlineKeyboardButton(user["name"], callback_data=str(idx))])
    keyboard.append([InlineKeyboardButton("🔙", callback_data="back")])
    return keyboard

def user_menu_prompt(app, chat_id: int) -> None:
    keyboard = []
    for idx, option in enumerate(MENU_OPTIONS):
        keyboard.append([InlineKeyboardButton(option, callback_data=str(idx))])
    keyboard.append([InlineKeyboardButton("🔙", callback_data="back")])
    return keyboard

async def handle_group_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    
    options = GROUPS
    for idx in range(len(chat_button_selections[chat_id])):
        options = options[chat_button_selections[chat_id][idx]]
    options_list = options if type(options) != dict else list(options.keys())
    
    if query.data == "back":
        chat_button_selections[chat_id].pop(-1)
    else:
        chat_button_selections[chat_id].append(options_list[int(query.data)])
    if len(chat_button_selections[chat_id]) >= 3: # 3 is maximum group depth rn, TODO change to by dynamic
        chat_prompt_state[chat_id] += 1
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
        return
    
    options = GROUPS
    for idx in range(len(chat_button_selections[chat_id])):
        options = options[chat_button_selections[chat_id][idx]]
    options_list = options if type(options) != dict else list(options.keys())
    
    keyboard = []
    for idx, group in enumerate(options_list):
        keyboard.append([InlineKeyboardButton(group, callback_data=str(idx))])
    if len(chat_button_selections[chat_id]) != 0:
        keyboard.append([InlineKeyboardButton("🔙", callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('אנא בחר את הקבוצות הרלוונטיות:', reply_markup=reply_markup)
        
async def handle_user_selection_button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'back':
        chat_prompt_state[chat_id] -= 1
    else:
        users = db.get_users_by_fields({GROUPS_CLASSES[i]: chat_button_selections[chat_id][i] for i in range(len(GROUPS_CLASSES))})
        chat_button_selections[chat_id].append(users[int(query.data)]["name"])
        chat_prompt_state[chat_id] += 1
    await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def handle_user_menu_button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'back':
        chat_button_selections[chat_id].pop(-1)
        chat_prompt_state[chat_id] -= 1
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
    else:
        chat_menu_state[chat_id] = [int(query.data), 0]
        await menu_options_prompts[int(query.data)][0]["prompt"](update, context)

async def button_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_button_states
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if chat_id in chat_menu_state.keys():
        await menu_options_prompts[chat_menu_state[chat_id][0]][chat_menu_state[chat_id][1]]["func"](update, context)
    else:
        await points_prompts[chat_prompt_state[chat_id]]["func"](update, context)

def authorize_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> list:
    keyboard = []
    keyboard.append([InlineKeyboardButton("אשר", callback_data='submit')])
    keyboard.append([InlineKeyboardButton("בטל", callback_data="cancel")])
    return keyboard

def _points_authorize_change(chat_id: int) -> str:
    user = db.get_users_by_groups(chat_button_selections[chat_id])[0]
    if chat_input[chat_id][0] < 0:
        chat_input[chat_id][0] = min(-1 * chat_input[chat_id][0], user[1]['points'])
        return f"להוריד מ{chat_button_selections[chat_id][-1]} {chat_input[chat_id][0]} נקודות?"
    else:
        return f"להוסיף ל{chat_button_selections[chat_id][-1]} {chat_input[chat_id][0]} נקודות?"

async def _handle_points_authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        if chat_input[chat_id][0] < 0:
            msg = f"ירדו ל{chat_button_selections[chat_id][-1]} {-1 * chat_input[chat_id][0]} נקודות."
        else:
            msg = f"הוספו ל{chat_button_selections[chat_id][-1]} {chat_input[chat_id][0]} נקודות."
        await query.edit_message_text(msg)
        user = db.get_users_by_groups(chat_button_selections[chat_id])[0]
        db.update_users_db({user[0]: {"points": user[1]["points"] + chat_input[chat_id][0]}})
    del chat_menu_state[chat_id]
    chat_input[chat_id] = []
    await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def _handle_points_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    try:
        number = int(update.message.text)  # Ensure the input is a valid number
        chat_input[chat_id].append(number)  # Store the input number
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
        
        chat_menu_state[chat_id][1] += 1
        await menu_options_prompts[chat_menu_state[chat_id][0]][chat_menu_state[chat_id][1]]["prompt"](update, context)
    except ValueError:
        await update.message.reply_text("הוזן קלט לא תקין. נסה שוב:")

async def handle_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    await menu_options_prompts[chat_menu_state[chat_id][0]][chat_menu_state[chat_id][1]]["func"](update, context)

async def _roles_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass

def _roles_menu_change(chat_id: int) -> str:
    return f"אנא סמן תפקידים שתרצה להוסיף ל{chat_button_selections[chat_id][-1]}:"

async def _handle_roles_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass

points_prompts = [{"prompt": init_button_prompt_func_generator('אנא בחר:', select_group_prompt, _prompt_init_func), "func": handle_group_button},
                {"prompt": button_prompt_func_generator('אנא בחר:', select_user_prompt), "func": handle_user_selection_button},
                {"prompt": button_prompt_func_generator('אנא בחר:', user_menu_prompt), "func": handle_user_menu_button}]
menu_options_prompts = [
    [
        {"prompt": text_prompt_func_generator('כמה נקודות להביא? (ניתן לשים - לצורך הורדת נקודות)'), "func": _handle_points_prompt},
        {"prompt": button_prompt_func_generator('בטוח?', authorize_prompt, change_prompt=_points_authorize_change), "func": _handle_points_authorize}
    ],
    [
        {"prompt": button_prompt_func_generator('איזה תפקיד להביא למשתמש?', _roles_menu, change_prompt=_roles_menu_change), "func": _handle_roles_menu}
    ]
]


BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "stats"
COMMAND_DESCRIPTION = "צפייה/עריכה של נתוני משתמשים"
ROLES = {"קלפ"}