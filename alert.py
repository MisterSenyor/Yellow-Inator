from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
import db
from api import APP, reset_handlers_to_default, text_prompt_func_generator, init_text_prompt_func_generator, button_prompt_func_generator, DEFAULT_INPUT_HANDLER, DEFAULT_BUTTON_HANDLER, INIT_AUTH_ENUM

import docx
from docx2pdf import convert
import os

chat_prompt_state = {} # {"id": idx for points_prompts}
chat_input = {} # {"id": (5, 3, 2)}
chat_selected_buttons = {} # {"id": {2,4,6}}


def _prompt_init_func(app, chat_id, chat_handlers) -> bool:
    if (user := db.get_user_by_chat_id(chat_id)) is None:
        return INIT_AUTH_ENUM["NOT_SIGNED_IN"]
    if ROLES != set() and list(set(user[1]["roles"]) & ROLES) == [] and not ("ADMIN" in user[1]["roles"]):
        return INIT_AUTH_ENUM["NO_PERMISSION"]
    chat_prompt_state[chat_id] = 0
    chat_input[chat_id] = [None] * 7  # Initialize the user's number as None
    chat_handlers[chat_id]["input"] = handle_input
    chat_handlers[chat_id]["button"] = button_handler_func
    return None


async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_input, chat_prompt_state
    chat_id = update.message.chat_id
    #print(chat_input, "\n", chat_id, "\n", chat_prompt_state)
    chat_input[chat_id][chat_prompt_state[chat_id]] = update.message.text  # Store the input
    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=context.user_data['message_id'])
    chat_prompt_state[chat_id] += 1
    await alert_prompts[chat_prompt_state[chat_id]]["prompt"](update, context)


async def handle_submit_button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    if query.data == 'submit':
        msg = "האירוע דווח!"
        await query.edit_message_text(msg)
        # Step 1: Open the Word document template
        doc = docx.Document("פורמט דיווח ראשוני.docx")

        # Step 2: Replace placeholders with actual values
        placeholders = {
            "הכנס_שם_אירוע": chat_input[chat_id][0],
            "הכנס_מדווח": chat_input[chat_id][1],
            "זמן": chat_input[chat_id][2],
            "מקום": chat_input[chat_id][3],
            "הכנס_תיאור": chat_input[chat_id][4],
            "הכנס_תוצאות": chat_input[chat_id][5],
            "הכנס_לקחים": chat_input[chat_id][6]
        }

        # Step 3: Replace placeholders while preserving formatting
        for paragraph in doc.paragraphs:
            for placeholder, value in placeholders.items():
                if placeholder in paragraph.text:
                    for run in paragraph.runs:
                        if placeholder in run.text:
                            run.text = run.text.replace(placeholder, value)

        # Step 4: Save the modified Word document
        output_docx = f"דיווח ראשוני {chat_input[chat_id][0]}.docx"
        doc.save(output_docx)
        convert(output_docx)
        os.remove(output_docx)
    reset_handlers_to_default(chat_id)


async def button_handler_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    await alert_prompts[chat_prompt_state[chat_id]]["func"](update, context)

def submit_prompt(app, chat_id: int) -> None:
    keyboard = []
    keyboard.append([InlineKeyboardButton("בטל דיווח", callback_data="cancel")])
    keyboard.append([InlineKeyboardButton("הגש דיווח", callback_data='submit')])
    return keyboard

def send_change_prompt(chat_id: int):
    return f"האם להגיש דיווח על {chat_input[chat_id][0]}?"

alert_prompts = [{"prompt": init_text_prompt_func_generator("שם האירוע:", _prompt_init_func), "func": None},
                {"prompt": text_prompt_func_generator("שם המדווח:"), "func": None},
                {"prompt": text_prompt_func_generator("תאריך ושעת האירוע:"), "func": None},
                {"prompt": text_prompt_func_generator("מיקום:"), "func": None},
                {"prompt": text_prompt_func_generator("תיאור האירוע:"), "func": None},
                {"prompt": text_prompt_func_generator("תוצאות האירוע:"), "func": None},
                {"prompt": text_prompt_func_generator("לקחים:"), "func": None},
                {"prompt": button_prompt_func_generator("מאשר?", submit_prompt, change_prompt=send_change_prompt), "func": handle_submit_button}]

# points_prompts = [{"prompt": init_text_prompt_func_generator("Enter name:", _prompt_init_func), "func": None},
                # {"prompt": text_prompt_func_generator("Enter number of points:"), "func": None},
                # {"prompt": button_prompt_func_generator("מאשר?", send_prompt, change_prompt=send_change_prompt), "func": handle_send_button}]


INPUT_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)
BUTTON_HANDLER = CallbackQueryHandler(button_handler_func)
COMMAND_NAME = "first_alert"
COMMAND_DESCRIPTION = "דיווח ראשוני על אירוע בטיחות"
ROLES = set()