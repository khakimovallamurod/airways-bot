from telegram.ext import CallbackContext, ConversationHandler
from telegram import Update
import keyboards
import asyncio
import db
import time
import get_airwasydata
from telegram import ReplyKeyboardRemove


USER_IDS = ['6889331565', '608913545', '1383186462']

FROM_CITY, TO_CITY, DATE, FL_NUM, SELECT, ADD_COMMENT = range(6)
ID_START = range(1)

async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    airwaydb = db.AirwayDB()

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
    airwaydb = db.AirwayDB()
    id_text = update.message.text
    chat_id = str(update.message.from_user.id)

    if chat_id in USER_IDS:
        if airwaydb.add_admin(id_text):
            await update.message.reply_text(
                f"✅ Foydalanuvchi muvaffaqiyatli adminlar ro'yxatiga qo‘shildi!\nID: {id_text}"
            )
            try:
                await context.bot.send_message(
                    chat_id=int(id_text),
                    text="🎉 Tabriklaymiz! Siz admin sifatida tizimga qo‘shildingiz."
                )
            except Exception as e:
                pass
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "⚠️ Kiritilgan ID noto‘g‘ri yoki bu foydalanuvchi allaqachon admin sifatida mavjud."
            )
    else:
        await update.message.reply_text(
            "⛔ Sizda foydalanuvchi qo‘shish huquqi yo‘q."
        )

    return ConversationHandler.END


async def railway_start(update: Update, context: CallbackContext):
    airwaydb = db.AirwayDB()
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
    if query.message:
        await query.message.delete()
        
    await query.message.reply_text("Sanani kiriting ushbu formatda (Year-Month-Day)!")
    return DATE

async def get_filghts_selected(update: Update, context: CallbackContext):
    context.user_data['date'] = update.message.text.strip()
    airwaydb = db.AirwayDB()
    waiting_message = await update.message.reply_text("⏳ Please wait, flight numbers are being identified...")

    date = context.user_data['date']
    if not airwaydb.is_valid_date(date):
        await update.message.reply_text("📅 You entered the date in the wrong format, please try again!")
        return DATE

    parser = get_airwasydata.FlightParser(
        from_city=context.user_data['from_city'].split(':')[1],
        to_city=context.user_data['to_city'].split(':')[1],
        date=context.user_data['date'],
        )
    
    flights: dict = await parser.find_missing_classes()
    await waiting_message.delete()

    if flights != {}:

        await update.message.reply_text("Select a flight number:", reply_markup=keyboards.select_flight_button(flights))
        return FL_NUM
    else:

        class_names = ['R', 'P', 'L', 'U', 'S', 'O', 'V', 'T', 'K', 'M', 'B', 'Y', 'I', 'D', 'C']
        await update.message.reply_text("Select a class type:", reply_markup=keyboards.select_class_button(class_names))
        return SELECT
    
async def select_class(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data  # misol: '1234:Y_P_R'
    parts = data.split(':')

    flight_number = parts[0]         
    class_list_str = parts[1]       
    classes = class_list_str.split('_')  

    context.user_data['flight_number'] = flight_number

    await query.edit_message_text(
        text=f"✈️ Flight HY {flight_number} selected.\n\nPlease select a class type:",
        reply_markup=keyboards.select_class_button(classes)
    )
    return SELECT
    
async def signal_start(update: Update, context: CallbackContext):
    """🚆 Signalni boshlash (InlineKeyboardMarkup orqali)"""

    query = update.callback_query
    await query.answer()
    class_data = query.data.split(':')
    context.user_data['class_name'] = class_data[1]
    await query.message.reply_text("💬 Comment qo'shing:")
    return ADD_COMMENT

async def add_comment_signal(update: Update, context: CallbackContext):
    context.user_data['comment'] = update.message.text.strip()
    chat_id = update.message.chat.id
    class_name = context.user_data['class_name']
    date = context.user_data['date']
    comment = context.user_data['comment']
    await update.message.reply_text(
        f"✈️ Econom {class_name} kuzatuv boshlandi!\n\nHar 3 daqiqada yangilanadi.",
    )

    if context.application is None or context.application.job_queue is None:
        await update.message.reply_text("⚠ Xatolik: Job Queue ishlamayapti!")
        return
    job_queue = context.application.job_queue
    job_name = f"signal_{chat_id}_{class_name}_{date}"
    
    job_queue.run_repeating(
        send_signal_job, interval=3*60, first=0, name=job_name,
        data={
            "chat_id": chat_id,
            "from_city": context.user_data['from_city'],
            "to_city": context.user_data['to_city'],
            "date": context.user_data['date'],
            "class_name": class_name,
            "comment": comment
        }
    )
    return ConversationHandler.END


async def send_signal_job(context: CallbackContext):
    """✈️ Rejalashtirilgan signal xabari (har bir poyezd uchun alohida)"""
    job = context.job  
    if job is None or "chat_id" not in job.data:
        return
    
    chat_id = job.data["chat_id"]
    date = job.data.get("date", None)
    stationFrom, stationFromCode = job.data["from_city"].split(':')
    stationTo, stationToCode = job.data["to_city"].split(':')
    signal_comment = job.data.get("comment")
    class_name = job.data.get('class_name')
    
    parser = get_airwasydata.FlightParser(
        from_city=stationFromCode,
        to_city=stationToCode,
        date=date,
        )
    obj = db.AirwayDB()
    add_for_data = {
                    'chat_id': chat_id,
                    'date': date,
                    'comment': signal_comment,
                    'class_name': class_name,
                    'active': True,
                    'route': [stationFrom, stationTo],
                    'stationFromCode':stationFromCode,
                    'stationToCode': stationToCode
    }
    parser_tariffs = await parser.run(class_name=f'Iqtisodiy {class_name}')
    if parser_tariffs == False or parser_tariffs==[]:
        results_signal_text = f"✈️ Econom {class_name} uchun joylar tekshirilmoqda...\n"
    
        
        obj.data_insert(data=add_for_data)
    else:
        
        route_key = f'{stationFromCode}_{stationToCode}'
        doc_id = f"{chat_id}_{class_name}_{date}_{route_key}"
        signal_datas = obj.get_signal_data(doc_id=doc_id)
        if not signal_datas:
            obj.data_insert(data=add_for_data)
        data = parser_tariffs[0]
        results_signal_text = (
            f"✈️ *{data['route']}*\n"
            f"📅 Sana: {data['date']}\n"
            f"🔢 Reys raqami: {data['flight_number']}\n"
            f"🛫 Uchish vaqti: {data['departure_time']}\n"
            f"🛬 Qo‘nish vaqti: {data['arrival_time']}\n"
            f"🛩️ Samolyot: {data['airplane']}\n"
            f"💺 Tariff: {data['tariff_type']} ({data['tariff_class']})\n"
            f"📦 Joylar soni: {data.get('available_seats', 'Nomaʼlum')}\n"
            f"💰 Narx: {data['price']} {data['currency']}"
        )
        
        reply_markup = keyboards.signal_keyboard(class_name, date=date, route_key=route_key)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📡 Signal: \n{results_signal_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def stop_signal(update: Update, context: CallbackContext):
    """🚫 Signalni to‘xtatish (InlineKeyboardMarkup orqali — Aviaparvozlar uchun)"""
    query = update.callback_query
    await query.answer()

    query_data = query.data.split(':')  # stop_signal:TAS_BHK:Econom_M:2025-07-18
    route_key = query_data[1]
    class_name = query_data[2]
    date = query_data[3]

    chat_id = update.effective_chat.id
    doc_id = f"{chat_id}_{class_name}_{date}_{route_key}"

    obj = db.AirwayDB()
    signal_datas = obj.get_signal_data(doc_id=doc_id)

    if not signal_datas:
        await query.message.reply_text("⚠ Xatolik: Signal ma'lumotlari topilmadi.")
        return

    from_city, to_city = signal_datas['route']
    comment = signal_datas.get('comment', '')
    active = signal_datas.get('active', False)

    results_signal_text = (
        f"✈️ {from_city} → {to_city}\n"
        f"📅 Sana: {date}\n"
        f"💺 Klass: {class_name}\n"
        f"💬 Comment: {comment}"
    )

    if not context.application or not context.application.job_queue:
        await query.message.reply_text("⚠ Xatolik: Job Queue topilmadi.")
        return

    job_name = f"signal_{chat_id}_{class_name}_{date}"
    current_jobs = context.application.job_queue.get_jobs_by_name(job_name)

    if current_jobs:
        if active:
            # ⛔ JOB'NI TO‘XTATISH (ENG MUHIM QISM)
            for job in current_jobs:
                job.schedule_removal()  # yoki job.cancel()

            # BAZADAGI STATUSNI YANGILASH
            obj.update_signal(doc_id=doc_id)

            await query.message.reply_text(f"🚫 Parvoz kuzatuvi to‘xtatildi.\n{results_signal_text}")
        else:
            await query.message.reply_text(f"🚫 Signal allaqachon to‘xtatilgan!")
    else:
        await query.message.reply_text("⚠ Aktiv kuzatuv topilmadi.")

    await asyncio.sleep(2)

async def view_actives(update: Update, context: CallbackContext):
    """📋 Faol aviaparvoz signallarini ko‘rsatish"""
    chat_id = update.message.chat.id
    airwayobj = db.AirwayDB()
    if airwayobj.check_admin(chat_id):
        actives_data = airwayobj.get_actives()
        if not actives_data:
            await update.message.reply_text("❌ Hech qanday aktiv signal topilmadi.")
            return

        job_queue = context.application.job_queue
        active_jobs = {job.name for job in job_queue.jobs()}
        found_active = False

        for act_data in actives_data:
            class_name = act_data['class_name']
            date = act_data['date']
            comment = act_data.get('comment', '')
            route = act_data['route']
            route_key = f"{act_data['stationFromCode']}_{act_data['stationToCode']}"

            job_name = f"signal_{chat_id}_{class_name}_{date}"
            if job_name in active_jobs:
                found_active = True

                results_signal_text = (
                    f"✈️ {route[0]} → {route[1]}\n"
                    f"📅 Sana: {date}\n"
                    f"💺 Klass: {class_name}\n"
                    f"💬 Comment: {comment}"
                )

                reply_markup = keyboards.signal_keyboard(class_name=class_name, date=date, route_key=route_key)

                await update.message.reply_text(
                    text=f"📌 Aktiv signal:\n{results_signal_text}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                await asyncio.sleep(1)

        if not found_active:
            await update.message.reply_text("❌ Faol aviaparvoz signal topilmadi.")
    else:
        await update.message.reply_text("❌ Siz bu botdan foydalana olmaysiz.")


async def restart_active_signals(application):
    airwaydb = db.AirwayDB()
    """Bot qayta ishga tushganda eski signallarni qayta tiklash"""
    actives_data = airwaydb.get_actives()

    job_queue = application.job_queue
    if not actives_data:
        print("⏳ Hech qanday aktiv signal topilmadi.")
        return
    
    for act_data in actives_data:
        chat_id = act_data['chat_id']
        date = act_data['date']
        from_city = f"{act_data['route'][0]}:{act_data['stationFromCode']}"
        to_city = f"{act_data['route'][1]}:{act_data['stationToCode']}"
        class_name = act_data.get('class_name', 'Noma’lum')
        comment = act_data.get('comment', '')

        job_name = f"signal_{chat_id}_{class_name}_{date}"

        job_queue.run_repeating(
            send_signal_job, interval=3*60, first=0, name=job_name,
            data={
                "chat_id": chat_id,
                "from_city": from_city,
                "to_city": to_city,
                "date": date,
                "class_name": class_name,
                "comment": comment
            }
        )


async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('❌ Jarayon bekor qilindi.')
    return ConversationHandler.END