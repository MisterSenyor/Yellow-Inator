from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import text_prompt_func_generator, init_text_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER

chat_selections = {}
chat_prompt_state = {}

chat_selected_options = {} # {"adfalksjdf": {2,4,6}}
button_states = []
state_idx = 0
participants = []

groups = db.get_groups()

def _prompt_init_func(app, chat_id):
    chat_prompt_state[chat_id] = 0
    chat_selections[chat_id] = []  # Initialize the user's number as None
    app.remove_handler(DEFAULT_INPUT_HANDLER)
    app.remove_handler(DEFAULT_BUTTON_HANDLER)
    app.add_handler(INPUT_HANDLER)  # Handle the number input
    app.add_handler(BUTTON_HANDLER)

def _fill_keyboard_by_group(keyboard, groups, idx=False):
    global state_idx
    if type(groups) == dict:
        for group in groups.keys():
            if idx:
                button_states.append(f"⚫ {group}")
                keyboard.append([InlineKeyboardButton(f"⚫ {group}", callback_data=str(len(button_states) - 1))])
            else:
                keyboard.append([InlineKeyboardButton(button_states[state_idx], callback_data=str(state_idx))])
                state_idx += 1
                
            if type(groups[group]) != dict:
                keyboard.append([])
                _fill_keyboard_by_group(keyboard[-1], groups[group], idx=idx)
            else:
                _fill_keyboard_by_group(keyboard, groups[group], idx=idx)
    elif type(groups) == list:
        for group in groups:
            if idx:
                button_states.append(f"⚫ {group}")
                keyboard.append(InlineKeyboardButton(f"⚫ {group}", callback_data=str(len(button_states) - 1)))
            else:
                print(f"{state_idx=}")
                print(len(keyboard))
                keyboard.append(InlineKeyboardButton(button_states[state_idx], callback_data=str(state_idx)))
                print(len(keyboard))
                state_idx += 1
    
def _fill_keyboard_by_participants(keyboard, users):
    for idx, user in enumerate(users):
        keyboard.append([InlineKeyboardButton(f"{user}", callback_data=idx)])

async def select_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global keyboard
    keyboard = []
    _fill_keyboard_by_group(keyboard, groups, idx=True)
    keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_id = update.message.chat_id
    chat_selected_options[chat_id] = set()
    
    await update.message.reply_text('קבוצות מהן לבחור משתתפים:', reply_markup=reply_markup) 

async def select_participants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global keyboard
    keyboard = []
    workaround_change_name_TODO = update if update.message is not None else update.callback_query
    chat_id = workaround_change_name_TODO.message.chat_id
    chosen_users = [x[0] for x in participants[:int(chat_selections[chat_id][1])]]
    _fill_keyboard_by_participants(keyboard, chosen_users)
    keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_selected_options[chat_id] = set()
    
    await workaround_change_name_TODO.edit_message_text('סמן אנשים שתרצה להחליף:', reply_markup=reply_markup) 
    
async def handle_group_button(update, context):
    global participants, button_states, state_idx
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        if chat_selected_options[chat_id]:
            participants = db.get_users_by_groups(chat_selected_options[chat_id])
            participants = sorted(participants, key=lambda x: x[1]["points"])
            participants_str = '\n'.join([x[0] for x in participants[:int(chat_selections[chat_id][1])]])
            await query.edit_message_text(f"המשתתפים הם:\n{participants_str}\nעם {chat_selections[chat_id][0]} נקודות לכל משתתף.")
            chat_prompt_state[chat_id] += 1
            await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
        else:
            await query.edit_message_text("No options selected.")
    else:
        # Toggle the state of the clicked option
        option = button_states[int(query.data)][2:]
        if int(query.data) < len(button_states):
            current_text = button_states[int(query.data)]
            if "⚫" in current_text:
                button_states[int(query.data)] = f"🔵 {option}"
                chat_selected_options[chat_id].add(option)
            else:
                button_states[int(query.data)] = f"⚫ {option}"
                chat_selected_options[chat_id].discard(option)
        
        # Rebuild the keyboard with updated states
        keyboard = []
        state_idx = 0
        _fill_keyboard_by_group(keyboard, groups)
        keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Please select multiple options:', reply_markup=reply_markup)

async def handle_swap_button(update, context):
    global participants, button_states, state_idx
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        participants_str = "\n".join([x[0] for x in participants[:int(chat_selections[chat_id][1])]])
        await query.edit_message_text(f"המשתתפים הם:\n{participants_str}\nעם {chat_selections[chat_id][0]} נקודות לכל משתתף.")
        chat_prompt_state[chat_id] += 1
    else:
        idx = int(query.data)
        if idx < len(button_states):
            participants.pop(idx)
            
            chosen_users = [x[0] for x in participants[:int(chat_selections[chat_id][1])]]
            keyboard = []
            _fill_keyboard_by_participants(keyboard, chosen_users)
            keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text('סמן אנשים שתרצה להחליף:', reply_markup=reply_markup) 

async def handle_number_input(update: Update, context) -> None:
    global chat_selections, chat_prompt_state
    chat_id = update.message.chat_id
    try:
        number = int(update.message.text)  # Ensure the input is a valid number
        chat_selections[chat_id].append(number)  # Store the input number
        # Delete the prompt message
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
        
        chat_prompt_state[chat_id] += 1
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
        
    except ValueError:
        await update.message.reply_text("Invalid input. Please input a valid number.")

async def button_handler_func(update: Update, context) -> None:
    global button_states, state_idx
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    global button_states, state_idx
    chat_id = query.message.chat_id
    await points_prompts[chat_prompt_state[chat_id]]["func"](update, context)
    

points_prompts = [{"prompt": init_text_prompt_func_generator("Enter number of points:", _prompt_init_func), "func": None},
                {"prompt": text_prompt_func_generator("Enter number of participants:"), "func": None},
                {"prompt": select_groups, "func": handle_group_button},
                {"prompt": select_participants, "func": handle_swap_button}]

INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "points"
