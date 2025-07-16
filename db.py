from tinydb import TinyDB, Query
from tinydb.table import Document
import base64
from datetime import datetime
import re
import hashlib

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
        
    def data_insert(self, data):
        if data.get('route') != None:
            route_key = f'{data['stationFromCode']}_{data['stationToCode']}'
            raw_id = f"{data['chat_id']}_{data['class_name']}_{data['date']}_{route_key}"
            doc_id = self.generate_doc_id(raw_id)
            data_one = Document(data, doc_id=doc_id)
            if self.check_data(doc_id):
                self.table.insert(data_one)
            else:
                self.table.update(data_one, doc_ids=[doc_id])
            return True
        return False
    def get_signal_data(self, doc_id):
        doc_id = self.generate_doc_id(doc_id)
        signal_data = self.table.get(doc_id=doc_id)
        return signal_data
    def generate_doc_id(self, doc_id):
        
        hash_str = hashlib.md5(doc_id.encode()).hexdigest()
        int_hash = int(hash_str, 16)
        octal_hash = int(oct(int_hash)[2:])  # 8-likka o‘tkazamiz (string oldidan "0o" olib tashlaymiz)
        return octal_hash
    
    def update_signal(self, doc_id):
        doc_id = int(self.generate_doc_id(doc_id))
        if self.table.get(doc_id=doc_id) != None:
            res = self.table.update({'active': False}, doc_ids=[doc_id])
            return True
        else :
            return False
    def check_data(self, doc_id):
        if self.table.get(doc_id=doc_id) == None:
            return True
        return False
    def get_actives(self):

        active_data = self.table.search(self.query.active == True)
        return active_data