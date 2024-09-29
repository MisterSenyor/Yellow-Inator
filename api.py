from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import db

groups = db.get_groups()
APP = ApplicationBuilder().token("7899662823:AAHg34XX6f2HedB9ONi_XArgTCgE4hv6q5E").build()
button_states = []
def text_prompt_func_generator(prompt: str) -> None:
    async def prompt_func(update: Update, context) -> None:
        global chat_prompt_state, chat_selections
        chat_id = update.message.chat_id
        print(f"{chat_id=}")
        message = await update.message.reply_text(prompt)
        context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
    return prompt_func

def init_text_prompt_func_generator(prompt: str, init_func) -> None:
    async def prompt_func(update: Update, context) -> None:
        global chat_prompt_state, chat_selections
        workaround_change_name_TODO = update if update.message is not None else update.callback_query
        chat_id = workaround_change_name_TODO.message.chat_id
        print(f"{chat_id=}")
        if not init_func(APP, chat_id):
            await update.message.reply_text("אנא הירשם בעזרת פקודת '/signup'")
            return
        if update.message is None:
            message = await update.callback_query.edit_message_text(prompt)
            print(f"MESSAGE = {message}")
            context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
        else:
            message = await update.message.reply_text(prompt)
            context.user_data['current_command'] = update.message.text.split()[0][1:]
            context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
    return prompt_func

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

def button_prompt_func_generator(prompt: str, setup_func, change_prompt=None, *args, **kwargs):
    async def func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        workaround_change_name_TODO = update if update.message is not None else update.callback_query
        chat_id = workaround_change_name_TODO.message.chat_id
        if change_prompt is not None:
            final_prompt = change_prompt(chat_id)
        else:
            final_prompt = prompt
        keyboard = setup_func(chat_id, *args, **kwargs)
        print(keyboard)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message is None:
            await update.callback_query.edit_message_text(final_prompt, reply_markup=reply_markup)
        else:
            await update.message.reply_text(final_prompt, reply_markup=reply_markup)
    return func

def reset_handlers_to_default(handlers: list) -> None:
    for handler in handlers:
        APP.remove_handler(handler)
    APP.add_handler(DEFAULT_INPUT_HANDLER)
    APP.add_handler(DEFAULT_BUTTON_HANDLER)

async def _default_input_handler(update: Update, context) -> None:
    
    await update.message.reply_text("Echo.")

async def _default_button_handler(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    await update.message.reply_text("Button pressed.")

DEFAULT_INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, _default_input_handler)
DEFAULT_BUTTON_HANDLER = CallbackQueryHandler(_default_button_handler)