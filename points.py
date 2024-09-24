from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

chat_selections = {}
chat_prompt_state = {}

selected_options = set()
button_states = {
    '0': '⚫ עילי מידד',
    '1': '⚫ עידו מנחה',
    '2': '⚫ אריאל ליבזון',
}

async def select_people(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    keyboard = [[InlineKeyboardButton(button_states[str(i)], callback_data=str(i))] for i in range(len(button_states.keys()))]
    keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text('Please select multiple options:', reply_markup=reply_markup) 
    
async def button_handler(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    if query.data == 'submit':
        print(f"{chat_id=}, {chat_selections[chat_id]=}")
        if selected_options:
            selected = ', '.join(selected_options)
            await query.edit_message_text(f"You selected: {selected}, with {chat_selections[chat_id][0]} points for {chat_selections[chat_id][1]} participants")
        else:
            await query.edit_message_text("No options selected.")
        return 
    else:
                # Toggle the state of the clicked option
        option = button_states[query.data][2:]
        if query.data in button_states:
            current_text = button_states[query.data]
            if "⚫" in current_text:
                # Change from red to blue and add to selected options
                button_states[query.data] = f"🔵 {option}"
                selected_options.add(option)
            else:
                # Change from blue to red and remove from selected options
                button_states[query.data] = f"⚫ {option}"
                selected_options.discard(option)
        
        # Rebuild the keyboard with updated states
        keyboard = [[InlineKeyboardButton(button_states[str(i)], callback_data=str(i))] for i in range(len(button_states.keys()))]
        keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
        
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

points_prompts = [prompt_func_generator("Enter number of points:", init=True),
                prompt_func_generator("Enter number of participants:"),
                select_people]

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
        await points_prompts[chat_prompt_state[chat_id]](update, context)
        
    except ValueError:
        await update.message.reply_text("Invalid input. Please input a valid number.")