from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import os
import db
from api import TEMP_DIR, APP, INIT_AUTH_ENUM, reset_handlers_to_default, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_input = {} # {"id": (5, 3, 2)}
chat_selected_buttons = {} # {"id": {2,4,6}}
chat_state_idx = {}
participants = []

groups = db.get_groups()

def _prompt_init_func(app, chat_id, chat_handlers) -> bool:
    if (user := db.get_user_by_chat_id(chat_id)) is None:
        return INIT_AUTH_ENUM["NOT_SIGNED_IN"]
    if type(ROLES) == set and list(set(user[1]["roles"]) & ROLES) == [] and not ("ADMIN" in user[1]["roles"]):
        return INIT_AUTH_ENUM["NO_PERMISSION"]
    chat_prompt_state[chat_id] = 0
    chat_input[chat_id] = [None, None]  # Initialize the user's number as None
    chat_handlers[chat_id]["input"] = handle_input
    chat_handlers[chat_id]["button"] = button_handler_func
    chat_handlers[chat_id]["file"] = file_handler_func
    return None

def confirm_prompt(app, chat_id: int) -> None:
    keyboard = []
    keyboard.append([InlineKeyboardButton("בטל", callback_data="cancel")])
    keyboard.append([InlineKeyboardButton("מאשר", callback_data='submit')])
    return keyboard

def confirm_change_prompt(chat_id: int):
    return f"אתה {chat_input[chat_id]}?"

async def handle_send_button(update, context: ContextTypes.DEFAULT_TYPE):
    global participants, button_states, state_idx
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        await query.edit_message_text(f"שלום, {chat_input[chat_id]}")
        reset_handlers_to_default(chat_id)
    else: # == "cancel"
        chat_prompt_state[chat_id] = 0
        chat_input[chat_id] = set()
        await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_input, chat_prompt_state
    # Manage signup
    chat_id = update.message.chat_id
    # if db.get_user_by_chat_id(chat_id) is not None:
    #     # Handle existing user
    #     return
    uid = update.message.text
    user = db.get_user_by_uid(uid)
    if user is None:
        # Handle nonexisting UID
        return
    chat_input[chat_id] = user[1]['name']
    user[1]['chat_id'] = chat_id
    db.update_users_db({user[0]: user[1]})
    chat_prompt_state[chat_id] += 1
    await points_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)

async def button_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global button_states, state_idx
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    global button_states, state_idx
    chat_id = query.message.chat_id
    await points_prompts[chat_prompt_state[chat_id]]["func"](update, context)

async def file_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document

    # Check if the uploaded file is an Excel file
    if document.mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
        file = await document.get_file()  # You need to await this!
        
        # Define the file path where the Excel file will be saved
        file_path = os.path.join(TEMP_DIR, document.file_name)
        print(f"GOT FILE. DOWNLOADING TO {file_path}")
        # Download the file asynchronously
        await file.download_to_drive(file_path)
        print(f"DOWNLOADED TO {file_path}")
        message = await update.message.reply_text(f"הקובץ התקבל: {document.file_name}. מנתח...")

        # Call the function to load and process the Excel file
        try:
            db.load_db_from_excel(file_path)
            print("FINISHED DOWNLOADING")
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=message.message_id)
            message = await update.message.reply_text(f"הקובץ נותח בהצלחה.")
        except BaseException as e:
            print(e)
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=message.message_id)
            await update.message.edit_text(f"הייתה תקלה בניתוח הקובץ. אנא פנה לקל\"פ או התייעץ עם המדריך.")
        chat_id = update.message.chat_id
        reset_handlers_to_default(chat_id)
    else:
        await update.message.reply_text("יש להעלות קבצי אקסל בלבד!")

points_prompts = [{"prompt": init_text_prompt_func_generator("אנא שלח קובץ אקסל בהתאם לפורמט:", _prompt_init_func), "func": None},
                  {"prompt": button_prompt_func_generator("מאשר?", confirm_prompt, change_prompt=confirm_change_prompt), "func": handle_send_button}]

INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
FILE_HANDLER = MessageHandler(filters.Document.ALL, file_handler_func)
COMMAND_NAME = "load_users"
COMMAND_DESCRIPTION = "טעינת משתמשים למאגר"
ROLES = set()