import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from enum import Enum
import db

groups = db.get_groups()
chat_handlers = {}
APP = ApplicationBuilder().token("7308402309:AAF-XK8EQxTdugA-rsebW9NrLkdtwRmwa4Y").build()
button_states = []
DEFAULT_DIR = "./default_files"
TEMP_DIR = "temp_excel_files"
INIT_AUTH_ENUM = {
    "NOT_SIGNED_IN": "אנא הירשם בעזרת פקודת '/signup'",
    "NO_PERMISSION": "אין לך הרשאות לפקודה הזו. אנא פנה לקל\"פ"
}


def text_prompt_func_generator(prompt: str) -> None:
    async def prompt_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        global chat_prompt_state, chat_selections
        workaround_change_name_TODO = update if update.message is not None else update.callback_query
        chat_id = workaround_change_name_TODO.message.chat_id
        print(f"{chat_id=}")
        if update.message is None:
            message = await update.callback_query.edit_message_text(prompt)
        else:
            message = await update.message.reply_text(prompt)
        context.user_data['message_id'] = message.message_id  # Store the message ID for later deletion
    return prompt_func

def init_text_prompt_func_generator(prompt: str, init_func) -> None:
    async def prompt_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        global chat_prompt_state, chat_selections
        workaround_change_name_todo = update if update.message is not None else update.callback_query
        chat_id = workaround_change_name_todo.message.chat_id
        chat_handlers[chat_id] = {}
        print(f"{chat_id=}")
        if (init_ret := init_func(APP, chat_id, chat_handlers)) is not None:
            await update.message.reply_text(init_ret)
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
        keyboard = setup_func(APP, chat_id, *args, **kwargs)
        print(keyboard)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message is None:
            await update.callback_query.edit_message_text(final_prompt, reply_markup=reply_markup)
        else:
            await update.message.reply_text(final_prompt, reply_markup=reply_markup)
    return func

def init_button_prompt_func_generator(prompt: str, setup_func, init_func, change_prompt=None, *args, **kwargs):
    async def func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        workaround_change_name_TODO = update if update.message is not None else update.callback_query
        chat_id = workaround_change_name_TODO.message.chat_id
        chat_handlers[chat_id] = {}
        if (init_ret := init_func(APP, chat_id, chat_handlers)) is not None:
            await update.message.reply_text(init_ret)
            return
        if change_prompt is not None:
            final_prompt = change_prompt(chat_id)
        else:
            final_prompt = prompt
        keyboard = setup_func(APP, chat_id, *args, **kwargs)
        print(keyboard)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message is None:
            await update.callback_query.edit_message_text(final_prompt, reply_markup=reply_markup)
        else:
            await update.message.reply_text(final_prompt, reply_markup=reply_markup)
    return func

def reset_handlers_to_default(chat_id: int) -> None:
    chat_handlers[chat_id] = {}

async def _default_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    workaround_change_name_todo = update if update.message is not None else update.callback_query
    chat_id = workaround_change_name_todo.message.chat_id
    print(chat_handlers)
    print(chat_id)
    if chat_id not in chat_handlers.keys() or "input" not in chat_handlers[chat_id].keys():
        await update.message.reply_text("Echo.")
        return
    await chat_handlers[chat_id]["input"](update, context)

async def _default_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    workaround_change_name_todo = update if update.message is not None else update.callback_query
    chat_id = workaround_change_name_todo.message.chat_id
    print(chat_handlers)
    print(chat_id)
    if chat_id not in chat_handlers.keys() or "button" not in chat_handlers[chat_id].keys():
        await query.answer()
        await update.message.reply_text("Button pressed.")
        return
    await chat_handlers[chat_id]["button"](update, context)

async def _default_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    workaround_change_name_todo = update if update.message is not None else update.callback_query
    chat_id = workaround_change_name_todo.message.chat_id

    if chat_id not in chat_handlers.keys() or "file" not in chat_handlers[chat_id].keys():
        await update.message.reply_text("Button pressed.")
        return
    await chat_handlers[chat_id]["file"](update, context)

DEFAULT_INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, _default_input_handler)
DEFAULT_BUTTON_HANDLER = CallbackQueryHandler(_default_button_handler)
DEFAULT_FILE_HANDLER = MessageHandler(filters.Document.ALL, _default_file_handler)