from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'hello {update.effective_user.first_name}')


# Global variable to store the user's input number
chat_selections = {}
chat_prompt_idx = {}

selected_options = set()
button_states = {
    '0': '⚫ Option 1',
    '1': '⚫ Option 2',
    '2': '⚫ Option 3',
}

async def select_people(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    keyboard = [[InlineKeyboardButton(button_states[str(i)], callback_data=str(i))] for i in range(len(button_states.keys()))]
    keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text('Please select multiple options:', reply_markup=reply_markup) 
    

async def button_handler(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'submit':
        if selected_options:
            selected = ', '.join(selected_options)
            await query.edit_message_text(f"You selected: {selected}")
        else:
            await query.edit_message_text("No options selected.")
        return 
    else:
                # Toggle the state of the clicked option
        option = f"Option {int(query.data) + 1}"
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

# Step 1: Prompt the user to input a number
def prompt_func_generator(prompt: str) -> None:
    async def prompt_func(update: Update, context) -> None:
        global user_number
        chat_id = update.message.chat_id
        user_number[chat_id] = []  # Initialize the user's number as None
        message = await update.message.reply_text(prompt)
        context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
    return prompt_func

points_prompts = [prompt_func_generator("Enter number of points:"),
                  prompt_func_generator("Enter number of participants:"),
                  select_people]

# Step 2: Handle the user's input and proceed to show the keyboard
async def handle_number_input(update: Update, context) -> None:
    global user_number
    chat_id = update.message.chat_id
    try:
        number = int(update.message.text)  # Ensure the input is a valid number
        user_number[chat_id].append(number)  # Store the input number

        # Delete the prompt message
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])

        # Proceed to show the keyboard options
        await points_prompts[prompt_num[chat_id]](update, context)
        
    except ValueError:
        await update.message.reply_text("Invalid input. Please input a valid number.")




def main():
    app = ApplicationBuilder().token("7899662823:AAHg34XX6f2HedB9ONi_XArgTCgE4hv6q5E").build()
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("points", prompt_number))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number_input))  # Handle the number input
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
    
    
if __name__ == "__main__":
    main()