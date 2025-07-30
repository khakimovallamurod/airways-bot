from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_viloyats():
    stations = {
        "Toshkent": "TAS",
        "Andijon": "AZN",
        "Buxoro": "BHK",
        "Farg'ona": "FEG",
        "Namangan": "NMA",
        "Nukus": "NCU",
        "Samarqand": "SKD",
        "Termiz": "TMJ",
        "Urganch": "UGC",
        "Navoiy": "NVI",
        "Qarshi": "KSQ",
        "Bishkek": "FRU",
        "Boku": "GYD",
        "Dehli":"DEL",
        "Almati":"ALA",
        "Dushanbe":"DYU",
        "Dubay":"DXB"
    }
    keyboards_btns = []
    row = []
    for viloyat in stations:
        row.append(InlineKeyboardButton(text=viloyat, callback_data=f'{viloyat}:{stations[viloyat]}'))
        if len(row) == 2:
            keyboards_btns.append(row)
            row = []

    if row:
        keyboards_btns.append(row)

    return InlineKeyboardMarkup(
        keyboards_btns
    )
    

def signal_keyboard(class_name, date, route_key):
    """🚆 Har bir signal uchun alohida 'To‘xtatish' tugmasi (InlineKeyboardMarkup)"""
    keyboard = [[InlineKeyboardButton(f"⛔ Econom {class_name} uchun to‘xtatish", callback_data=f"stop_signal:{route_key}:{class_name}:{date}")]]
    return InlineKeyboardMarkup(keyboard)

def select_class_button(selected_classes, class_names):
    keyboard_btn = []
    row = []

    for i, cls in enumerate(class_names):
        is_selected = cls in selected_classes
        label = f"{'✅ ' if is_selected else ''}Econom {cls}"
        callback_data = f'toggle_class:{cls}'
        row.append(InlineKeyboardButton(text=label, callback_data=callback_data))

        if (i + 1) % 2 == 0:
            keyboard_btn.append(row)
            row = []

    if row:
        keyboard_btn.append(row)

    # Yakuniy tasdiqlash tugmasi
    keyboard_btn.append([
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data='confirm_classes')
    ])

    return InlineKeyboardMarkup(keyboard_btn)

def select_flight_button(flights: dict, more_flights: dict):
    keyboard_btns = []
    custom_order = ['R', 'P', 'L', 'U', 'S', 'O', 'V', 'T', 'K', 'M', 'B', 'Y', 'I', 'D', 'C']
    for number, classes in flights.items():
        sorted_classes = sorted(classes, key=lambda x: custom_order.index(x))
        classes_text = '_'.join(sorted_classes)
        button = InlineKeyboardButton(text=f"❇️ HY {number}", callback_data=f'{number}:{classes_text}')
        keyboard_btns.append([button]) 
    for number, classes in more_flights.items():
        sorted_classes = sorted(classes, key=lambda x: custom_order.index(x))
        classes_text = '_'.join(sorted_classes)
        button = InlineKeyboardButton(text=f"✴️ HY {number}", callback_data=f'{number}:{classes_text}')
        keyboard_btns.append([button]) 
        
    return InlineKeyboardMarkup(keyboard_btns)