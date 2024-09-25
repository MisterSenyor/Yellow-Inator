from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import db

chat_selections = {}
chat_prompt_state = {}

selected_options = {}
button_states = []
state_idx = 0

groups = db.get_groups()

def _fill_keyboard_by_group(keyboard, groups, idx=False):
    global state_idx
    if type(groups) == dict:
        for group in groups.keys():
            if idx:
                button_states.append(f"⚫ {group}")
                keyboard.append([InlineKeyboardButton(f"⚫ {group}", callback_data=str(len(button_states) - 1))])
            else:
                print(f"{state_idx=}")
                print(len(keyboard))
                keyboard.append([InlineKeyboardButton(button_states[state_idx], callback_data=str(state_idx))])
                print(len(keyboard))
                state_idx += 1
            # keyboard.append([str(group)])
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
            # keyboard.append(str(group))
    
def _fill_keyboard_by_participants(keyboard, users):
    for idx, user in users:
        keyboard.append([InlineKeyboardButton(f"⚫ {user[0]}", callback_data=idx)])

async def select_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global keyboard
    keyboard = []
    button_states = []
    _fill_keyboard_by_group(keyboard, groups, idx=True)
    keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_id = update.message.chat_id
    selected_options[chat_id] = set()
    
    await update.message.reply_text('קבוצות מהן לבחור משתתפים:', reply_markup=reply_markup) 

async def select_participants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global keyboard
    keyboard = []
    button_states = []
    _fill_keyboard_by_participants(keyboard, chosen_users)
    keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_id = update.message.chat_id
    selected_options[chat_id] = set()
    
    await update.message.reply_text('קבוצות מהן לבחור משתתפים:', reply_markup=reply_markup) 
    
async def button_handler(update: Update, context) -> None:
    global button_states, state_idx
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    points_prompts[chat_prompt_state[chat_id]]["func"](query)
    return

async def handle_group_button(query):
    global button_states, state_idx
    print("GOT CALLED")
    chat_id = query.message.chat_id
    if query.data == 'submit':
        print(f"{chat_id=}, {chat_selections[chat_id]=}")
        if selected_options[chat_id]:
            participants = db.get_users_by_groups(selected_options[chat_id])
            print(participants)
            participants = sorted(participants, key=lambda x: x[1]["points"])
            print("SORTED:")
            print(participants)
            participants = participants[:int(chat_selections[chat_id][1])]
            print(participants)
            participants_str = '\n'.join([x[0] for x in participants])
            await query.edit_message_text(f"המשתתפים הם:\n{participants_str}\nעם {chat_selections[chat_id][0]} נקודות לכל משתתף.", reply_markup=[])
        else:
            await query.edit_message_text("No options selected.")
    else:
                # Toggle the state of the clicked option
        option = button_states[int(query.data)][2:]
        if int(query.data) < len(button_states):
            current_text = button_states[int(query.data)]
            print(f"{current_text=}")
            if "⚫" in current_text:
                # Change from red to blue and add to selected options
                button_states[int(query.data)] = f"🔵 {option}"
                selected_options[chat_id].add(option)
            else:
                # Change from blue to red and remove from selected options
                button_states[int(query.data)] = f"⚫ {option}"
                selected_options[chat_id].discard(option)
        
        print("BUTTON STATES -------")
        print(button_states)
        # Rebuild the keyboard with updated states
        keyboard = []
        state_idx = 0
        _fill_keyboard_by_group(keyboard, groups)
        keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
        
        print("ASSEMBLED KEYBOARD -------")
        print(keyboard)
        print("DONE")
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Please select multiple options:', reply_markup=reply_markup)


def prompt_func_generator(prompt: str, init=False) -> None:
    async def prompt_func(update: Update, context) -> None:
        global chat_prompt_state, chat_selections
        chat_id = update.message.chat_id
        print(f"{chat_id=}")
        if init:
            chat_prompt_state[chat_id] = 0
            chat_selections[chat_id] = []  # Initialize the user's number as None
        message = await update.message.reply_text(prompt)
        context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
    return prompt_func


# Step 2: Handle the user's input and proceed to show the keyboard
async def handle_number_input(update: Update, context) -> None:
    global chat_selections, chat_prompt_state
    chat_id = update.message.chat_id
    try:
        number = int(update.message.text)  # Ensure the input is a valid number
        print(f"GOT NUMBER {number}")
        chat_selections[chat_id].append(number)  # Store the input number
        print(f"{chat_id=}, {chat_selections[chat_id]=}")

        # Delete the prompt message
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])

        # Proceed to show the keyboard options
        chat_prompt_state[chat_id] += 1
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)
        
    except ValueError:
        await update.message.reply_text("Invalid input. Please input a valid number.")



points_prompts = [{"prompt": prompt_func_generator("Enter number of points:", init=True), "func": None},
                {"prompt": prompt_func_generator("Enter number of participants:"), "func": None},
                {"prompt": select_groups, "func": handle_group_button},
                {"prompt": select_participants, "func": None}]

#TODO: button_states global declaration for proper display of herirarchy