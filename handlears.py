from telegram.ext import CallbackContext, ConversationHandler
from telegram import Update
import keyboards
import asyncio
import db
import time

USER_IDS = ['6889331565', '608913545', '1383186462']
airwaydb = db.AirwayDB()

FROM_CITY, TO_CITY, DATE = range(3)
ID_START = range(1)


async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    chat_id = user.id
    if airwaydb.check_admin(chat_id):
        await update.message.reply_text(
            text=f"""Assalomu aleykum {user.full_name}. Ushbu bot yordamida joylar sonini aniqlashingiz mumkin. /airwaystart""",
        )
    else:
        await update.message.reply_text(
            text=f"""Assalomu aleykum {user.full_name}. Siz bu botdan foydalana olmaysiz 😔""",
        )

async def admin_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Foydalnuvchi IDsini yuboring.")
    return ID_START

async def insert_admin(update: Update, context: CallbackContext):
    id_text = update.message.text
    chat_id = str(update.message.from_user.id)
    if chat_id in USER_IDS :
        if airwaydb.add_admin(id_text):
            await update.message.reply_text("Foydalanuvchi qo'shildi ✅")
            return ConversationHandler.END
        else:
            await update.message.reply_text("ID xato yoki User allaqachon mavjud ❌")
    else:
        await update.message.reply_text("Siz foydalanuvchi qo'sholmaysiz ❌")

    return ConversationHandler.END

async def railway_start(update: Update, context: CallbackContext):
    chat_id = update.message.from_user.id

    if airwaydb.check_admin(chat_id):
        msg = await update.message.reply_text("Poyezd tanlash boshlandi!!!")
        context.user_data["last_message"] = msg.message_id
        
        return await get_from_city(update, context)
    else:
        await update.message.reply_text(
            text=f"""Siz bu botdan foydalana olmaysiz 😔""",
        )
async def safe_delete_message(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"[Xatolik] Xabarni o‘chirishda muammo: {e}")

async def get_from_city(update: Update, context: CallbackContext):
    if "last_message" in context.user_data:
        await safe_delete_message(context.bot, update.message.chat_id, context.user_data["last_message"])

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.message.delete()
        except Exception as e:
            print(f"Xatolik (delete_message): {e}") 

        msg = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="FROM:",
            reply_markup=keyboards.get_viloyats()
        )

    else:
        msg = await context.bot.send_message(
            chat_id=update.message.chat_id,
            text="FROM:",
            reply_markup=keyboards.get_viloyats()
        )

    context.user_data["last_message"] = msg.message_id
    return FROM_CITY

async def from_city_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['from_city'] = query.data
    
    return await get_to_city(update, context)

async def get_to_city(update: Update, context: CallbackContext):
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        if query.message:
            try:
                await query.message.delete()
            except Exception as e:
                print(f"Xatolik (delete_message): {e}")

            msg = await context.bot.send_message(
                chat_id=query.message.chat_id, 
                text="TO:",
                reply_markup=keyboards.get_viloyats()  
            )
        else:
            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,  
                text="TO:",
                reply_markup=keyboards.get_viloyats()  
            )

    else:
        msg = await update.message.reply_text(
            text="TO:",
            reply_markup=keyboards.get_viloyats()
        )

    context.user_data["last_message"] = msg.message_id
    return TO_CITY

async def to_city_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['to_city'] = query.data
    
    await query.message.reply_text("Sanani kiriting ushbu formatda (Year-Month-Day)!")
    return DATE
async def select_class(update: Update, context: CallbackContext):
    context.user_data['date'] = update.message.text.strip()
    date = context.user_data['date']

    if not airwaydb.is_valid_date(date):
        await update.message.reply_text("Sanani noto'g'ri formatda kiritdingiz, iltimos qayta urinib ko'ring (Year-Month-Day)!")
        return DATE
    
    print(date)
    print(context.user_data['from_city'])
    print(context.user_data['to_city'])



async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Amalyot bajarilmadi!')
    return ConversationHandler.END