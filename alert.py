"""
from points import *
import aspose.words as aw

chat_inputs = {}

async def submit_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global keyboard
    keyboard = []
    button_states = []
    keyboard.append([InlineKeyboardButton("Submit Selection", callback_data='submit')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_id = update.message.chat_id
    chat_selected_options[chat_id] = set()
    
    await update.message.reply_text('דווח:', reply_markup=reply_markup) 


async def handle_submit_button(update, context: ContextTypes.DEFAULT_TYPE):
    global participants
    query = update.callback_query
    print("HANDLE!")
    global button_states, state_idx
    print("GOT CALLED")
    chat_id = query.message.chat_id
    if query.data == 'submit':
        msg = "האירוע דווח!"
        generate_alert(update, context)
        await query.edit_message_text(msg)
        chat_prompt_state[chat_id] += 1
    else:
        print("ERROR")


def generate_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Step 1: Open the Word document "test.docx"
    doc = aw.Document("פורמט דיווח ראשוני.docx")

    # Step 2: Create a copy of the document and modify only the copy
    doc_copy = doc.deep_clone()

    # Step 3: Find and replace text in the copy
    chat_id = update.message.chat_id
    doc_copy.range.replace("הכנס_שם_אירוע", chat_inputs[chat_id][0], aw.replacing.FindReplaceOptions())
    doc_copy.range.replace("הכנס_מדווח", chat_inputs[chat_id][1], aw.replacing.FindReplaceOptions())
    doc_copy.range.replace("הכנס_תאריך_ושעה", chat_inputs[chat_id][2], aw.replacing.FindReplaceOptions())
    doc_copy.range.replace("הכנס_מיקום", chat_inputs[chat_id][3], aw.replacing.FindReplaceOptions())
    doc_copy.range.replace("הכנס_תיאור", chat_inputs[chat_id][4], aw.replacing.FindReplaceOptions())
    doc_copy.range.replace("הכנס_תוצאות", chat_inputs[chat_id][5], aw.replacing.FindReplaceOptions())
    doc_copy.range.replace("הכנס לקחים", chat_inputs[chat_id][6], aw.replacing.FindReplaceOptions())
    

    # Step 4: Save the modified Word document as a PDF
    doc_copy.save(f"דיווח ראשוני {chat_inputs[chat_id][0]}.pdf")




alert_prompts = [{"prompt": prompt_func_generator("תיאור האירוע:", init=True), "func": None},
                {"prompt": prompt_func_generator("שם המדווח:"), "func": None},
                {"prompt": prompt_func_generator("תאריך ושעת האירוע:"), "func": None},
                {"prompt": prompt_func_generator("מיקום:"), "func": None},
                {"prompt": prompt_func_generator("תיאור האירוע:"), "func": None},
                {"prompt": prompt_func_generator("תוצאות האירוע:"), "func": None},
                {"prompt": prompt_func_generator("לקחים:"), "func": None},
                {"prompt": submit_button, "func": handle_submit_button}]
"""