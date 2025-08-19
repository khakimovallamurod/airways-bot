from telegram.ext import CallbackContext, ConversationHandler
from telegram import Update
import keyboards
import asyncio
import db
import time
import get_airwasydata
from telegram import ReplyKeyboardRemove
import os
from collections import defaultdict, deque
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from datetime import datetime

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")
scheduler = AsyncIOScheduler(
    timezone=TASHKENT_TZ,
    job_defaults={
        "coalesce": True,          
        "max_instances": 1,        
        "misfire_grace_time": 5, 
    },
)
USER_IDS = ['6889331565', '608913545', '1383186462']

FROM_CITY, TO_CITY, DATE, FL_NUM, SELECT, ADD_COMMENT = range(6)
ACCOUNT_NAME, ID_START = range(2)
REMOVE_ID = range(1)
EDIT_COMMENT = range(1)

async def start(update: Update, context: CallbackContext):
    user = update.message.chat
    airwaydb = db.AirwayDB()
    chat_id = user.id
    if airwaydb.check_admin(chat_id):
        await update.message.reply_text(
            text=f"""Hello {user.full_name}! 👋\n\nUsing this bot, you can monitor seat availability for flights.\nType /airwaystart to begin.""",
        )
    else:
        await update.message.reply_text(
            text=f"""Hello {user.full_name}. 😔\nYou are not authorized to use this bot.""",
        )


async def admin_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Please send the user Name.")
    return ACCOUNT_NAME

async def admin_name(update: Update, context: CallbackContext):
    context.user_data['admin_name'] = update.message.text.capitalize()
    await update.message.reply_text("Please send the user ID.")
    return ID_START

async def insert_admin(update: Update, context: CallbackContext):
    airwaydb = db.AirwayDB()
    id_text = update.message.text
    chat_id = str(update.message.chat.id)
    acount_name = context.user_data['admin_name'] 
    if chat_id in USER_IDS:
        if airwaydb.add_admin(chat_id=id_text, fio=acount_name):
            await update.message.reply_text(
                f"✅ User successfully added to the admin list!\nAdmin: {acount_name}"
            )
            try:
                await context.bot.send_message(
                    chat_id=int(id_text),
                    text="🎉 Congratulations! You have been added to the system as an admin."
                )
            except Exception as e:
                pass
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "⚠️ The entered ID is invalid or this user already exists as an administrator."
            )
    else:
        await update.message.reply_text(
            "⛔ You do not have permission to add users."
        )

    return ConversationHandler.END

async def view_all_admin(update: Update, context: CallbackContext):
    airwaydb = db.AirwayDB()
    chat_id = update.effective_chat.id
    if str(chat_id) in USER_IDS:
        admin_list = airwaydb.view_admins()
        admin_texts = ""
        for admin in admin_list:
            admin_texts += f"{admin['account_name']} ----- {admin['chat_id']}\n"
        await update.message.reply_text(admin_texts)
    else:
        await update.message.reply_text("⛔ You can't see admin lists")

async def remove_start(update: Update, context: CallbackContext):
    
    await update.message.reply_text("Please send the ID to delete the user.")
    return REMOVE_ID

async def remove_admin(update: Update, context: CallbackContext):
    airwaydb = db.AirwayDB()
    chat_id = update.effective_chat.id
    delet_id = update.message.text
    if str(chat_id) in USER_IDS:
        if airwaydb.delete_admin(delet_id):
            await update.message.reply_text("✅ This user was removed from the list")
            return ConversationHandler.END
        else:
            await update.message.reply_text("⚠️ This user doesn't exist")
            return ConversationHandler.END
    else:
        await update.message.reply_text("⛔ You can't delete user")
        return ConversationHandler.END


async def airway_start(update: Update, context: CallbackContext):
    airwaydb = db.AirwayDB()
    chat_id = update.message.chat.id

    if airwaydb.check_admin(chat_id):
        msg = await update.message.reply_text("Flight selection has started!!!")
        context.user_data["last_message"] = msg.message_id
        
        return await get_from_city(update, context)
    else:
        await update.message.reply_text(
            text=f"""You are not authorized to use this bot 😔""",
        )
async def safe_delete_message(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"[Xatolik] Xabarni o‘chirishda muammo: {e}")

async def get_from_city(update: Update, context: CallbackContext):
    if "last_message" in context.user_data:
        await safe_delete_message(context.bot, update.message.chat.id, context.user_data["last_message"])

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

    try:
        await query.message.delete()
    except Exception as e:
        print(f"Xatolik (delete_message): {e}")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📅 Please enter the date in the format YYYY-MM-DD (e.g., 2025-07-21):"
    )

    return DATE

async def get_filghts_selected(update: Update, context: CallbackContext):
    context.user_data['date'] = update.message.text.strip()
    airwaydb = db.AirwayDB()
    waiting_message = await update.message.reply_text("⏳ Please wait, flight numbers are being identified...")

    date = context.user_data['date']
    if not airwaydb.is_valid_date(date):
        await update.message.reply_text("📅 You entered the date in the wrong format, please try again!")
        return DATE
    from_city = context.user_data['from_city'].split(':')[1]
    to_city = context.user_data['to_city'].split(':')[1]
    parser = get_airwasydata.FlightParser(
        from_city=from_city,
        to_city=to_city,
        date=context.user_data['date'],
        )
    
    flights: dict = await parser.find_missing_classes()
    await waiting_message.delete()
    more_flights = airwaydb.get_flights_between_cities(from_city, to_city, flights)
    if flights != {} or more_flights != {}:

        await update.message.reply_text("Select a flight number:", reply_markup=keyboards.select_flight_button(flights, more_flights))
        return FL_NUM
    else:

        class_names = ['R', 'P', 'L', 'U', 'S', 'O', 'V', 'T', 'K', 'M', 'B', 'Y', 'I', 'D', 'C']
        context.user_data['available_classes'] = class_names
        context.user_data['selected_classes'] = []

        await update.message.reply_text(
            "Select a class type:",
            reply_markup=keyboards.select_class_button([], class_names)
        )
        return SELECT
    
async def select_class(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if ':' in data and data.startswith('toggle_class'):
        cls = data.split(':')[1]
        selected = context.user_data.get('selected_classes', [])
        if cls in selected:
            selected.remove(cls)
        else:
            selected.append(cls)

        context.user_data['selected_classes'] = selected
        class_names = context.user_data.get('available_classes', [])
        await query.edit_message_reply_markup(
            reply_markup=keyboards.select_class_button(selected, class_names)
        )
        return SELECT

    elif data == 'confirm_classes':
        selected = context.user_data.get('selected_classes', [])
        if not selected:
            await query.edit_message_text("⚠️ Please select at least one class.")
            return SELECT
        context.user_data['flight_number'] = context.user_data.get('flight_number_select')
        context.user_data['confirmed_classes'] = selected
        await query.edit_message_text(
            f"✅ Selected classes: {', '.join(selected)}\n\nWrite a comment:"
        )
        return ADD_COMMENT

    else:
        flight_number, class_str = data.split(':')
        classes = class_str.split('_')
        context.user_data['flight_number_select'] = flight_number
        context.user_data['available_classes'] = classes
        context.user_data['selected_classes'] = []

        await query.edit_message_text(
            f"✈️ HY {flight_number} flight selected.\n\nPlease select a class:",
            reply_markup=keyboards.select_class_button([], classes)
        )
        return SELECT

async def add_comment_signal(update: Update, context: CallbackContext):
    context.user_data['comment'] = update.message.text.strip()
    chat_id = update.message.chat.id
    date = context.user_data['date']
    comment = context.user_data['comment']
    class_names = context.user_data.get('confirmed_classes', [])

    if not class_names:
        await update.message.reply_text("⚠ No class selected.")
        return ConversationHandler.END

    await update.message.reply_text(
        f"✈️ Signals started for classes: {', '.join(class_names)}\n\nUpdates will be sent every 3 minutes."
    )
    stationFrom, stationFromCode = context.user_data['from_city'].split(':')
    stationTo, stationToCode = context.user_data['to_city'].split(':')
    obj = db.AirwayDB()
    for class_name in class_names:
        add_for_data = {
            'chat_id': chat_id,
            'date': date,
            'comment': comment,
            'class_name': class_name,
            'active': True,
            'route': [stationFrom, stationTo],
            'stationFromCode': stationFromCode,
            'stationToCode': stationToCode, 
            'flight_number': context.user_data.get('flight_number')
        }
        obj.data_insert(data = add_for_data)
    job_name = f"signal_{chat_id}_{'_'.join(class_names)}_{date}" 

    if scheduler.get_job(job_name):
        scheduler.remove_job(job_name)   
    interval_num = random.randint(120, 150)
    scheduler.add_job(
        send_signal_job,
        "interval",
        seconds=interval_num,
        id=job_name,
        kwargs={
            "bot": context.bot,
            'data' : {
                'chat_id': chat_id,
                'from_city': context.user_data['from_city'],
                'to_city': context.user_data['to_city'],
                'date': date,
                'class_name': class_names,
                'comment': comment,
                'flight_number': context.user_data.get('flight_number')
            }
        }
    )
    return ConversationHandler.END

chat_queues = defaultdict(deque)
chat_locks = defaultdict(asyncio.Lock)
async def send_signal_job(bot, data):
    
    chat_id = data["chat_id"]
    chat_queues[chat_id].append(data)
    
    if not chat_locks[chat_id].locked():
        asyncio.create_task(process_queue(chat_id, bot))

async def process_queue(chat_id, bot):
    async with chat_locks[chat_id]:
        while chat_queues[chat_id]:
            data = chat_queues[chat_id].popleft()
            try:
                await handle_signal_job(bot, data)
            except Exception as e:
                print(f"❌ Xatolik ({chat_id}):", e)


async def handle_signal_job(bot, data):
    chat_id = data["chat_id"]
    date = data.get("date")
    stationFrom, stationFromCode = data["from_city"].split(':')
    stationTo, stationToCode = data["to_city"].split(':')
    signal_comment = data.get("comment")
    class_names = data.get("class_name", [])
    flight_number = data.get("flight_number")
    parser = get_airwasydata.FlightParser(
        from_city=stationFromCode,
        to_city=stationToCode,
        date=date,
    )

    parser_results = await parser.run(class_name=class_names, flight_number=flight_number) 
    folder = "results"
    if os.path.exists(folder) and os.path.isdir(folder):
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        if len(files) > 20:
            for filename in files:
                os.remove(os.path.join(folder, filename))

    route_key = f'{stationFromCode}_{stationToCode}'
    matching_tariffs = [t for t in parser_results if t['tariff_class'] in class_names]
    for match_tarif in matching_tariffs:
        data = match_tarif

        if data.get("is_multi_segment", False) and data.get("segments"):
            segments_text = ""
            for segment in data["segments"]:
                segments_text += (
                    f"✈️ Segment {segment['segment_number']}:\n"
                    f"   🛫 {segment['from']} -> {segment['to']}\n"
                    f"   🕒 {segment['departure_time']} - {segment['arrival_time']}\n"
                    f"   🛩️ {segment['airplane']}\n"
                    f"   🆔 Flight Number: {segment['flight_number']}\n\n"
                )
            results_signal_text = (
                f"📅 Date: {data['date']}\n"
                f"🛬 Route: {data['route']}\n"
                f"💺 Tariff: {data['tariff_type']} ({data['tariff_class']})\n"
                f"📦 Available Seats: {data.get('available_seats', 'Unknown')}\n"
                f"💰 Price: {data['price']} {data['currency']}\n"
                f"🔁 Refund Fee: {int(data['refund_fee'])/10000} {data['refund_currency']}\n"
                f"💬 Comments: {signal_comment}\n\n"
                f"📋 Segments:\n{segments_text}"
            )
        else:
            results_signal_text = (
                f"✈️ *{data['route']}*\n"
                f"📅 Date: {data['date']}\n"
                f"🔢 Flight Number: {data['flight_number']}\n"
                f"🛫 Departure Time: {data['departure_time']}\n"
                f"🛬 Arrival Time: {data['arrival_time']}\n"
                f"🛩️ Aircraft: {data['airplane']}\n"
                f"💺 Tariff: {data['tariff_type']} ({data['tariff_class']})\n"
                f"📦 Available Seats: {data.get('available_seats', 'Unknown')}\n"
                f"💰 Price: {data['price']} {data['currency']}\n"
                f"🔁 Air ticket refund: {int(data['refund_fee'])/10000} {data['refund_currency']}\n"
                f"💬 Comments: {signal_comment}"
            )

        reply_markup = keyboards.signal_keyboard(data['tariff_class'], date=date, route_key=route_key)
        await bot.send_message(
            chat_id=chat_id,
            text=f"📡 Signal:\n{results_signal_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def stop_signal(update: Update, context: CallbackContext):
    """🚫 Signalni to‘xtatish (biror klass uchun)"""
    query = update.callback_query
    await query.answer()

    _, route_key, class_name_to_remove, date = query.data.split(':')
    chat_id = query.message.chat.id
    obj = db.AirwayDB()

    jobs = scheduler.get_jobs()
    target_job = None
    job_classes = []
    
    for job in jobs:
        parts = job.id.split('_')  
        job_chat_id = parts[1]
        job_classes = parts[2:-1]
        job_date = parts[-1]

        if str(chat_id) == job_chat_id and str(date) == job_date and class_name_to_remove in job_classes:
            target_job = job
            break

    if not target_job:
        await query.message.reply_text("⚠️ No active tracking found for this class.")
        return

    doc_id = f"{chat_id}_{class_name_to_remove}_{date}_{route_key}"
    signal_data = obj.get_signal_data(doc_id=doc_id)

    if not signal_data:
        await query.message.reply_text("⚠️ Signal not found or already stopped in database.")
        return

    active = signal_data.get('active', False)
    from_city, to_city = signal_data['route']
    comment = signal_data.get('comment', '')
    flight_number = signal_data.get('flight_number')

    if not active:
        await query.message.reply_text("ℹ️ This signal has already been stopped.")
        return

    scheduler.remove_job(target_job.id)
    obj.update_signal(doc_id=doc_id)  

    updated_classes = [c for c in job_classes if c != class_name_to_remove]

    results_signal_text = (
        f"✈️ {from_city} → {to_city}\n"
        f"🔢 Flight Number: {flight_number}\n"
        f"📅 Date: {date}\n"
        f"💺 Tariff: {class_name_to_remove}\n"
        f"💬 Comment: {comment}"
    )

    if updated_classes:
        new_job_name = f"signal_{chat_id}_{'_'.join(updated_classes)}_{date}"
        new_from_city = f"{from_city}:{signal_data.get('stationFromCode', '')}"
        new_to_city = f"{to_city}:{signal_data.get('stationToCode', '')}"
        interval_num = random.randint(120, 150)
        scheduler.add_job(
            send_signal_job,
            "interval",
            seconds=interval_num,
            id=new_job_name,
            kwargs={
                "bot": context.bot,
                'data' : {
                    'chat_id': chat_id,
                    'from_city': new_from_city,
                    'to_city': new_to_city,
                    'date': date,
                    'class_name': updated_classes,
                    'comment': comment,
                    'flight_number': flight_number
                }
            },
            replace_existing=True
        )
        await query.message.reply_text(
            f"🚫 Signal for tariff '{class_name_to_remove}' stopped.\n"
            f"ℹ️ Other tariffs ({', '.join(updated_classes)}) continue to run.\n\n"
            f"{results_signal_text}"
        )
    else:
        await query.message.reply_text(
            f"🚫 All signals for tariff '{class_name_to_remove}' stopped.\n\n"
            f"{results_signal_text}"
        )
async def stop_signal_by_classes(update: Update, context: CallbackContext):
    """🚫 Signalni to‘xtatish (biror klass uchun)"""
    query = update.callback_query
    await query.answer()
    _, route_key, class_names, date = query.data.split(':')
    chat_id = query.message.chat.id
    obj = db.AirwayDB()
    job_name = f"signal_{chat_id}_{class_names}_{date}"
    target_job = scheduler.get_job(job_name)
    class_names_list = class_names.split('_')
    if target_job:
        doc_id = f"{chat_id}_{class_names_list[0]}_{date}_{route_key}"
        signal_data = obj.get_signal_data(doc_id=doc_id)
        for class_name in class_names_list:
            doc_id_one = f"{chat_id}_{class_name}_{date}_{route_key}"
            obj.update_signal(doc_id=doc_id_one)
        
        from_city, to_city = signal_data['route']
        comment = signal_data.get('comment', '')
        flight_number = signal_data.get('flight_number')
        results_signal_text = (
            f"✈️ {from_city} → {to_city}\n"
            f"🔢 Flight Number: {flight_number}\n"
            f"📅 Date: {date}\n"
            f"💺 Tariff: {', '.join(class_names_list)}\n"
            f"💬 Comment: {comment}"
        )
        await query.message.reply_text(
            f"🚫 All signals for tariff '{', '.join(class_names_list)}' stopped.\n\n"
            f"{results_signal_text}"
        )
        scheduler.remove_job(job_name)
    else:
        await query.message.reply_text("⚠️ No active tracking found for this class.")
        return
async def stop_all_byid(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    airwayobj = db.AirwayDB()
    jobs = scheduler.get_jobs()
    total = 0
    for job in jobs:
        parts = job.id.split('_')  
        job_chat_id = parts[1]
        if job_chat_id == str(chat_id):
            job_classes = parts[2:-1]    
            scheduler.remove_job(job_id=job.id)
            total += len(job_classes)
    actives_data = airwayobj.get_actives(chat_id=chat_id)
    for act_data in actives_data:
        date = act_data['date']
        class_name = act_data['class_name']
        from_code = act_data['stationFromCode']
        to_code = act_data['stationToCode']
        route_key = f"{from_code}_{to_code}" 
        doc_id = f"{chat_id}_{class_name}_{date}_{route_key}"
        airwayobj.update_signal(doc_id=doc_id)
    if total != 0:
        await update.message.reply_text(
            f"✅ {total} active signal(s) have been successfully canceled."
        )
    else:
        await update.message.reply_text(
            "ℹ️ You don’t have any active signals at the moment."
        )

async def view_actives(update: Update, context: CallbackContext):
    """📋 Faol aviaparvoz signallarini ko‘rsatish (multi-class formatda)"""
    chat_id = update.message.chat.id
    airwayobj = db.AirwayDB()
    if not airwayobj.check_admin(chat_id):
        await update.message.reply_text("❌ You are not authorized to view active signals.")
        return

    actives_data = airwayobj.get_actives(chat_id=chat_id)
    if actives_data == []:
        await update.message.reply_text("❌ No active signals found.")
        return

    for act_data in actives_data:
        class_name = act_data['class_name']
        date = act_data['date']
        comment = act_data.get('comment', '')
        route = act_data['route']
        from_code = act_data['stationFromCode']
        to_code = act_data['stationToCode']
        flight_number = act_data['flight_number']
        route_key = f"{from_code}_{to_code}"

        results_signal_text = (
            f"✈️ {route[0]} → {route[1]}\n"
            f"🔢 Flight Number: {flight_number}\n"
            f"📅 Date: {date}\n"
            f"💺 Tariff: {class_name}\n"
            f"💬 Comment: {comment}"
        )
        reply_markup = keyboards.signal_keyboard(
            class_name=class_name, 
            date=date, 
            route_key=route_key
        )

        await update.message.reply_text(
            text=f"📌 Active signal:\n{results_signal_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await asyncio.sleep(1)

async def view_actives_by_classes(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    airwayobj = db.AirwayDB()
    if not airwayobj.check_admin(chat_id):
        await update.message.reply_text("❌ You are not authorized to view active signals.")
        return

    actives_data = airwayobj.get_actives(chat_id=chat_id)
    if actives_data == []:
        await update.message.reply_text("❌ No active signals found.")
        return
    grouped = defaultdict(lambda: {
        'chat_id': None,
        'from_city': None,
        'to_city': None,
        'date': None,
        'class_name': [],
        'comment': None,
        'flight_number': None,
    })

    for item in actives_data:
        key = (
            item['chat_id'],
            item['stationFromCode'],
            item['stationToCode'],
            item['date'],
            item.get('comment', ''),
            item.get('flight_number', None),
        )
        entry = grouped[key]
        if entry['chat_id'] is None:
            entry['chat_id'] = item['chat_id']
            entry['from_city'] = f"{item['route'][0]}:{item['stationFromCode']}"
            entry['to_city'] = f"{item['route'][1]}:{item['stationToCode']}"
            entry['date'] = item['date']
            entry['comment'] = item.get('comment', '')
            entry['flight_number'] = item.get('flight_number', None)
        cls = item.get('class_name')
        if cls:
            if isinstance(cls, list):
                for c in cls:
                    if c not in entry['class_name']:
                        entry['class_name'].append(c)
            else:
                if cls not in entry['class_name']:
                    entry['class_name'].append(cls)

    results = list(grouped.values())  
    for act_data in results:
        from_city, from_cityCode = act_data['from_city'].split(':')
        to_city, to_cityCode = act_data['to_city'].split(':')
        class_name = act_data['class_name']
        date = act_data['date']
        comment = act_data.get('comment', '')
        flight_number = act_data['flight_number']
        results_signal_text = (
            f"✈️ {from_city} → {to_city}\n"
            f"🔢 Flight Number: {flight_number}\n"
            f"📅 Date: {date}\n"
            f"💺 Tariff: {', '.join(class_name)}\n"
            f"💬 Comment: {comment}"
        )
        reply_markup = keyboards.signal_keyboard_by_classes(
            class_name=class_name, 
            date=date, 
            route_key=f'{from_cityCode}_{to_cityCode}'
        )

        await update.message.reply_text(
            text=f"📌 Active signal:\n{results_signal_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        await asyncio.sleep(1)

async def restart_active_signals(application):
    airwaydb = db.AirwayDB()
    actives_data = airwaydb.get_actives()

    if not actives_data:
        print("⏳ Hech qanday aktiv signal topilmadi.")
        return

    grouped = defaultdict(lambda: {
        'chat_id': None,
        'from_city': None,
        'to_city': None,
        'date': None,
        'class_name': [],
        'comment': None,
        'flight_number': None,
    })

    for item in actives_data:
        key = (
            item['chat_id'],
            item['stationFromCode'],
            item['stationToCode'],
            item['date'],
            item.get('comment', ''),
            item.get('flight_number', None),
        )

        entry = grouped[key]

        if entry['chat_id'] is None:
            entry['chat_id'] = item['chat_id']
            entry['from_city'] = f"{item['route'][0]}:{item['stationFromCode']}"
            entry['to_city'] = f"{item['route'][1]}:{item['stationToCode']}"
            entry['date'] = item['date']
            entry['comment'] = item.get('comment', '')
            entry['flight_number'] = item.get('flight_number', None)

        cls = item.get('class_name')
        if cls:
            if isinstance(cls, list):
                for c in cls:
                    if c not in entry['class_name']:
                        entry['class_name'].append(c)
            else:
                if cls not in entry['class_name']:
                    entry['class_name'].append(cls)

    results = list(grouped.values())  
    
    for data in results:
        job_name = f"signal_{data['chat_id']}_{'_'.join(data['class_name'])}_{data['date']}"
        current_jobs = scheduler.get_job(job_name)
        if current_jobs:
            continue
        interval_num = random.randint(120, 150)
        scheduler.add_job(
            send_signal_job,
            "interval",
            seconds=interval_num,
            id=job_name,
            kwargs={
                "bot": application.bot,
                'data' : data
            },
            replace_existing=True
        )

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('❌ Jarayon bekor qilindi.')
    return ConversationHandler.END

async def ask_new_comment(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    context.user_data["edit_message_id"] = query.message.message_id
    context.user_data["edit_keyboard"] = query.message.reply_markup
    context.user_data['query_data'] = query.data
    prompt_message = await query.message.reply_text("✍️ Enter a new comment:")
    context.user_data['prompt_message_id'] = prompt_message.message_id
    context.user_data['prompt_chat_id'] = prompt_message.chat.id

    return EDIT_COMMENT

async def save_new_comment(update: Update, context: CallbackContext):
    if "edit_message_id" not in context.user_data:
        return

    new_comment = update.message.text
    chat_id = update.message.chat_id
    message_id = context.user_data["edit_message_id"]

    message = await context.bot.forward_message(
        chat_id=chat_id,
        from_chat_id=chat_id,
        message_id=message_id
    )
    old_text = message.text
    await message.delete()

    idx = 0
    lines = old_text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith("💬 Comment:"):
            idx = index
            lines[index] = f"💬 Comment: {new_comment}"
    new_text = "\n".join(lines[:idx+1])

    query_data = context.user_data['query_data']
    _, route_key, class_names_list, date = query_data.split(':')
    obj = db.AirwayDB()
    success = False
    for class_name in class_names_list.split('_'):
        doc_id = f"{chat_id}_{class_name}_{date}_{route_key}"
        update_com = obj.update_comment(doc_id=doc_id, new_comment=new_comment)
        if update_com:
            success = True
    old_keyboard = context.user_data.get("edit_keyboard")
    if success: 
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=new_text,
            reply_markup=old_keyboard
        )
    else:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=old_text,
            reply_markup=old_keyboard
        )

    await context.bot.delete_message(
        chat_id=context.user_data['prompt_chat_id'],
        message_id=context.user_data['prompt_message_id']
    )
    await update.message.delete()
    del context.user_data['prompt_message_id']
    del context.user_data['prompt_chat_id']
    del context.user_data["edit_message_id"]
    del context.user_data["edit_keyboard"]
    del context.user_data["query_data"]

    return ConversationHandler.END