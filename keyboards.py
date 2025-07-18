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
        "Boku": "GYD"
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
    
def poyezd_licanse(numbers):
    keyboards_btns = []
    row = []
    for num in numbers:
        row.append(KeyboardButton(text=num))
        if len(row) == 2:
            keyboards_btns.append(row)
            row = []
    if row:
        keyboards_btns.append(row)

    return ReplyKeyboardMarkup(
        keyboards_btns,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def signal_keyboard(class_name, date, route_key):
    """🚆 Har bir signal uchun alohida 'To‘xtatish' tugmasi (InlineKeyboardMarkup)"""
    keyboard = [[InlineKeyboardButton(f"⛔ Econom {class_name} uchun to‘xtatish", callback_data=f"stop_signal:{route_key}:{class_name}:{date}")]]
    return InlineKeyboardMarkup(keyboard)

def select_class_button(class_names):
    keyboard_btn = []
    row = []

    for i, cls in enumerate(class_names):
        callback_data = f'class_selected:{cls}'
        btn = InlineKeyboardButton(text=f'Econom {cls}', callback_data=callback_data)
        row.append(btn)

        if (i + 1) % 2 == 0:
            keyboard_btn.append(row)
            row = []

    if row:
        keyboard_btn.append(row)

    return InlineKeyboardMarkup(keyboard_btn)


def select_flight_button(flights: dict):
    keyboard_btns = []

    for number, classes in flights.items():
        classes_text = '_'.join(classes)
        button = InlineKeyboardButton(text=f"HY {number}", callback_data=f'{number}:{classes_text}')
        keyboard_btns.append([button]) 
        
    return InlineKeyboardMarkup(keyboard_btns)