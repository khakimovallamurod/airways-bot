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
        "Qarshi": "KSQ"
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
    raw_keyboard = []
    for indx in range(0, len(class_names)):
        raw_keyboard.append(KeyboardButton(text=f'Econom {class_names[indx]}'))
        if (indx + 1)%3 == 0:
            keyboard_btn.append(raw_keyboard)
            raw_keyboard = []
    if raw_keyboard != []:
        keyboard_btn.append(raw_keyboard)

    return ReplyKeyboardMarkup(keyboard=keyboard_btn, resize_keyboard=True)
