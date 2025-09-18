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

    def add_admin(self, chat_id, fio):
        enc_id = self.simple_encrypt(str(chat_id))
        if not self.check_admin(chat_id):
            self.admintable.insert({'chat_id': enc_id, "account_name": fio})
            return True
        else :
            return False
    
    def delete_admin(self, chat_id):
        enc_id = self.simple_encrypt(str(chat_id))
        if self.check_admin(chat_id):
            self.admintable.remove(self.query.chat_id == enc_id)
            return True
        else:
            return False

    def view_admins(self):
        all_chat_ids = self.admintable.all()
        all_admins = []
        for admin in all_chat_ids:
            decode_id = self.simple_decrypt(admin['chat_id'])
            all_admins.append(
                {
                    'chat_id':decode_id,
                    'account_name': admin['account_name']
                }
            )
        return all_admins

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
            route_key = f"{data['stationFromCode']}_{data['stationToCode']}"
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
        octal_hash = int(oct(int_hash)[2:])  
        return octal_hash
    
    def update_signal(self, doc_id):
        doc_id = int(self.generate_doc_id(doc_id))
        if self.table.get(doc_id=doc_id) != None:
            res = self.table.update({'active': False}, doc_ids=[doc_id])
            return True
        else :
            return False
    
    def update_comment(self, doc_id, new_comment):
        doc_id = int(self.generate_doc_id(doc_id))
        if self.table.get(doc_id=doc_id) != None:
            res = self.table.update({'comment': new_comment}, doc_ids=[doc_id])
            return True
        else :
            return False
        
    def check_data(self, doc_id):
        if self.table.get(doc_id=doc_id) == None:
            return True
        return False
    
    def get_actives(self, chat_id = None):
        if chat_id == None:
            return self.table.search(self.query.active == True)
        return self.table.search(
            (self.query.active == True) & (self.query.chat_id == chat_id)
        )
    def get_flights_between_cities(self, from_code, to_code, missing_flights):
    
        flight_data = {
        "SKD": {
            "TAS": ["41", "43", "45"],
            "BHK": ['52', '41', '22', '45', '56', '62']
        },
        "UGC": {
            "TAS": ["51", "53", "55", "57", "61", "62"]
        },
        "NMA": {
            "TAS": ["93", "94"]
        },
        "FEG": {
            "TAS": ["85", "81"]
        },
        "BHK": {
            "TAS": ["61", "21", "22", "56"],
            "SKD": ['52', '41', '22', '45', '56', '62']
        },
        "TMJ": {
            "TAS": ["69", "70"]
        },
        "NCU": {
            "TAS": ["11", "13", "15", "17", "12"]
        },
        "KSQ": {
            "TAS": ["72", "21"]
        },
        "JFK": {
            "TAS": [
                "7292", "282", "274", "7282", "7318", 
                "272", "7284", "102"
            ]
        },
        "TLV": {
            "TAS": [
                "302", "304", "815", "258", "809", 
                "258", "807", "258"
            ]
        },
        "TAS": {
            "SKD": ["42", "44", "46"],
            "UGC": ["51","52", "53", "54", "55", "56", "57", "58", "61", "62"],
            "NMA": ["94", "93"],
            "FEG": ["82", "86"],
            "BHK": ["61", "21", "22", "56"],
            "TMJ": ["70", "69"],
            "NCU": ["12", "16", "18", "14"],
            "KSQ": ["21", "72"],
            "JFK": [
                "281", "7283", "7281", "7291", "7317",
                "271", "7281", "7291", "7317", "7283",
                "273", "7317", "7283", "7281", "7291",
                "101"
            ],
            "TLV": [
                "301", "303", "257", "810", "806", "812"
            ]
        }
        }
    
        flight_numbers = flight_data.get(from_code, {}).get(to_code, {})
        filtered_flights = [num for num in flight_numbers if num not in missing_flights]
        default_missing_seats = ['B', 'C', 'D', 'I', 'K', 'L', 'O', 'P', 'R', 'S', 'T', 'U', 'V', 'Y', 'M']
        result = {fn: default_missing_seats for fn in filtered_flights}
        return result


