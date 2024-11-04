from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
import sys
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import APP, INIT_AUTH_ENUM, init_button_prompt_func_generator, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER, reset_handlers_to_default

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_button_selections = {} # {id: current selections (e.g. erez -> erez, harel -> erez, harel, 22)}
chat_input = {}
chat_menu_state = {}
GROUPS_CLASSES = ["battalion", "company", "team"]
GROUPS = db.get_groups()

def _prompt_init_func(app, chat_id, chat_handlers):
    if (user := db.get_user_by_chat_id(chat_id)) is None:
        return INIT_AUTH_ENUM["NOT_SIGNED_IN"]
    if type(ROLES) == set and list(set(user[1]["roles"]) & ROLES) == [] and not ("ADMIN" in user[1]["roles"]):
        return INIT_AUTH_ENUM["NO_PERMISSION"]
    chat_prompt_state[chat_id] = 0
    chat_handlers[chat_id]["input"] = handle_number_input
    chat_handlers[chat_id]["button"] = button_handler_func
    if chat_id not in list(chat_button_selections.keys()):
        chat_button_selections[chat_id] = [] 
    chat_input[chat_id] = []
    return None

def select_group_prompt(app, chat_id: int) -> None:
    keyboard = []
    options = GROUPS
    for idx in range(len(chat_button_selections[chat_id])):
        options = options[chat_button_selections[chat_id][idx]]
    options_list = options if type(options) != dict else list(options.keys())
    
    for idx, group in enumerate(options_list):
        keyboard.append([InlineKeyboardButton(group, callback_data=str(idx))])
    if len(chat_button_selections[chat_id]) != 0:
        keyboard.append([InlineKeyboardButton("🔙", callback_data="back")])
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

def _generate_groups_prompt(chat_id: int) -> str:
    options = GROUPS
    for idx in range(len(chat_button_selections[chat_id])):
        options = options[chat_button_selections[chat_id][idx]]
    options_list = options if type(options) != dict else list(options.keys())
    users = db.get_users_by_groups_OR(chat_button_selections[chat_id])
    
    point_avg = int((lambda d: sum(map(lambda x: x[1]['points'], d)) / len(d))(users))
    max_points_avg = ("", -1)
    min_points_avg = ("", sys.maxsize * 2 + 1)
    for option in options_list:
        users = db.get_users_by_groups_AND(chat_button_selections[chat_id] + [option])
        nested_point_avg = int((lambda d: sum(map(lambda x: x[1]['points'], d)) / len(d))(users))
        if nested_point_avg > max_points_avg[1]:
            max_points_avg = (option, nested_point_avg)
        if nested_point_avg <= min_points_avg[1]:
            min_points_avg = (option, nested_point_avg)
    
    return f'מידע על {", ".join(chat_button_selections[chat_id])}\n\nממוצע נקודות: {point_avg}\nממוצע גבוה ביותר - {max_points_avg[0]}: {max_points_avg[1]}\nממוצע נמוך ביותר - {min_points_avg[0]}: {min_points_avg[1]}\n\nאנא בחר:'

def _generate_users_prompt(chat_id: int) -> str:
    users = db.get_users_by_groups_AND(chat_button_selections[chat_id])
    point_avg = int((lambda d: sum(map(lambda x: x[1]['points'], d)) / len(d))(users))
    max_user = max(users, key=lambda x: x[1]['points'])[1]
    min_user = min(users, key=lambda x: x[1]['points'])[1]
    
    return f'מידע על {", ".join(chat_button_selections[chat_id])}\n\nממוצע נקודות: {point_avg}\nצוער עם מקס נקודות - {max_user["name"]}: {max_user["points"]}\nצוער עם מינ נקודות - {min_user["name"]}: {min_user["points"]}\n\nאנא בחר:'

def _generate_menu_prompt(chat_id: int) -> str:
    user = db.get_users_by_groups_AND(chat_button_selections[chat_id])[0]
    return f'מידע על {user[1]["name"]}\n\nסך נקודות: {user[1]["points"]}\n\nאנא בחר:'
        
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
    
    await query.edit_message_text(_generate_groups_prompt(chat_id), reply_markup=reply_markup)
        
async def handle_user_selection_button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'back':
        chat_button_selections[chat_id].pop()
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
    user = db.get_users_by_groups_AND(chat_button_selections[chat_id])[0]
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
        user = db.get_users_by_groups_AND(chat_button_selections[chat_id])[0]
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

def roles_menu(app, chat_id: int) -> None:
    keyboard = []
    print(f"TEST - {chat_button_selections[chat_id]=}")
    user = db.get_users_by_groups_AND(chat_button_selections[chat_id])[0]
    print(user[1]["name"])
    for role in list(set(db.get_roles())):
        if role in user[1]["roles"]:
            keyboard.append([InlineKeyboardButton(f"🔵 {role}", callback_data=f"🔵 {role}")])
        else:
            keyboard.append([InlineKeyboardButton(f"⚫ {role}", callback_data=f"⚫ {role}")])
    keyboard.append([InlineKeyboardButton("🔙", callback_data="back")])
    print(f"TEST ---------------\n{keyboard=}")
    return keyboard
            

def _roles_menu_change(chat_id: int) -> str:
    # return f"אנא סמן תפקידים שתרצה להוסיף ל{chat_button_selections[chat_id][-1]}:"
    user = db.get_user_by_chat_id(chat_id)
    return f'ניהול תפקידים למשתמש {user[1]["name"]}:'
    

async def _handle_roles_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    chosen_button = query.data
    user = db.get_users_by_groups_AND(chat_button_selections[chat_id])[0]
    if chosen_button == "back":
        del chat_menu_state[chat_id]
        chat_input[chat_id] = []
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
    if chosen_button[0] == "⚫": # add role
        user[1]["roles"].append(chosen_button[2:])
    else: # remove role
        user[1]["roles"].remove(chosen_button[2:])
    db.update_users_db({user[0]: user[1]})
    keyboard = roles_menu(None, chat_id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(f'ניהול תפקידים למשתמש {user[1]["name"]}:', reply_markup=reply_markup)
    

points_prompts = [{"prompt": init_button_prompt_func_generator('אנא בחר:', select_group_prompt, _prompt_init_func), "func": handle_group_button},
                {"prompt": button_prompt_func_generator('אנא בחר:', select_user_prompt, change_prompt=_generate_users_prompt), "func": handle_user_selection_button},
                {"prompt": button_prompt_func_generator('אנא בחר:', user_menu_prompt, change_prompt=_generate_menu_prompt), "func": handle_user_menu_button}]
menu_options_prompts = [
    [
        {"prompt": text_prompt_func_generator('כמה נקודות להביא? (ניתן לשים - לצורך הורדת נקודות)'), "func": _handle_points_prompt},
        {"prompt": button_prompt_func_generator('בטוח?', authorize_prompt, change_prompt=_points_authorize_change), "func": _handle_points_authorize}
    ],
    [
        {"prompt": button_prompt_func_generator('איזה תפקיד להביא למשתמש?', roles_menu, change_prompt=_roles_menu_change), "func": _handle_roles_menu}
    ]
]
MENU_OPTIONS = [
    "הוסף/הורד נקודות",
    "הוסף/הורד הרשאות"
]

BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "stats"
COMMAND_DESCRIPTION = "צפייה/עריכה של נתוני משתמשים"
ROLES = {"קלפ"}