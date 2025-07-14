from tinydb import TinyDB, Query
from tinydb.table import Document
import base64
from datetime import datetime
import re

class AirwayDB:
    def __init__(self):
        self.db = TinyDB('airway_data.json', indent=4)
        self.table = self.db.table("AirwayDB")
        self.query = Query()
        self.adminfile = TinyDB('admin_chatIDs.json', indent=4)
        self.admintable = self.adminfile.table('AdminTokens')
    # 1 Admin add and check
    def simple_encrypt(self, text):
        encoded = base64.b64encode(text.encode()).decode()
        return encoded[::-1]

    def simple_decrypt(self, encoded):
        reversed_text = encoded[::-1]
        decoded = base64.b64decode(reversed_text.encode()).decode()
        return decoded

    def add_admin(self, chat_id):
        enc_id = self.simple_encrypt(str(chat_id))
        if not self.check_admin(chat_id):
            self.admintable.insert({'chat_id': enc_id})
            return True
        else :
            return False

    def check_admin(self, chat_id):
        enc_id = self.simple_encrypt(str(chat_id))
        
        result = self.admintable.search(self.query.chat_id == enc_id)
        return len(result) > 0
    # ======== #
    # 2 check date 
    def is_valid_date(self, date: str) -> bool:
        """Sanani YYYY-MM-DD formatida tekshiradi."""
        pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, date):
            return False
        try:
            datetime.strptime(date, "%Y-%m-%d")
            return True
        except ValueError:
            return False
