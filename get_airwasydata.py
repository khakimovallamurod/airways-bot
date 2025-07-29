from bs4 import BeautifulSoup
import re
import json
import config
import os
from playwright.async_api import async_playwright
from datetime import datetime
import hashlib
from collections import defaultdict
import re

class FlightParser:
    all_possible_classes = ['R', 'P', 'L', 'U', 'S', 'O', 'V', 'T', 'K', 'M', 'B', 'Y', 'I', 'D', 'C']

    def __init__(self, from_city, to_city, date):
        self.file_path = None
        self.html_content = ""
        self.soup = None
        self.flight_info = {}
        self.url = config.get_url()
        self.from_city = from_city
        self.to_city = to_city
        self.date = date
        self.class_name = None

    async def load_browser(self):
        part_url = f'from={self.from_city}&to={self.to_city}&date1={self.date}&currency=UZS&locale=en&adults=1&children=0&infants=0'
        base_url = f'{self.url}?{part_url}'
        os.makedirs("result", exist_ok=True)
        flight_date = datetime.strptime(self.date, "%Y-%m-%d").date()
        today = datetime.today().date()
        
        if flight_date < today:
            return False
                
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(base_url, wait_until="networkidle", timeout=60000)
            redirect_url = page.url.split('?')[0].split('/')[-1]
            self.file_path = f"result/{redirect_url}"
            
            html_content = await page.content()
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            await browser.close()
        return True

    async def load_file(self):
        load_browser = await self.load_browser()
        if not load_browser:
            return False
        
        with open(self.file_path, 'r', encoding='utf-8') as file:
            self.html_content = file.read()
        self.soup = BeautifulSoup(self.html_content, 'html.parser')
        
        return True
    
    def extract_flight_info(self):
        try:
            ticket = self.soup.find('div', class_='booking-ticket-item', id='segmentfirst')
            if not ticket:
                return {}

            self.flight_info = {
                'flight_number': ticket.find('div', class_='booking-ticket-item-number flight').get_text(strip=True),
                'from': ticket.find('div', class_='booking-ticket-item-direction fromto_name').find_all('span')[0].get_text(strip=True),
                'to': ticket.find('div', class_='booking-ticket-item-direction fromto_name').find_all('span')[1].get_text(strip=True),
                'departure_time': ticket.find('div', class_='booking-ticket-item-time deptime').get_text(strip=True),
                'arrival_time': ticket.find('div', class_='booking-ticket-item-time text-right arrtime').get_text(strip=True),
                'departure_date': ticket.find('div', class_='booking-ticket-item-date depdate').get_text(separator=' ', strip=True),
                'arrival_date': ticket.find('div', class_='booking-ticket-item-date text-right arrdate').get_text(separator=' ', strip=True),
                'airplane': ticket.find('div', class_='booking-ticket-item-flight-airplane board').get_text(strip=True)
            }
            return self.flight_info

        except Exception as e:
            print(f"[Xatolik] Reys ma'lumotlarini olishda: {e}")
            return {}

    def parse_tariffs(self, flight_number=None):
        results = []
        flight_map = {}
        
        for span in self.soup.select('#OWtime_form .timeowglobalclass'):
            code = span.get('data-time')
            number = span.find('span', class_='flight-data')
            if number:
                flight_map[code] = "HY " + number.get_text(strip=True)
        
        flight_info_data = {}
        script_tags = self.soup.find_all('script')
        for script in script_tags:
            if script.string and 'window.flightinfo' in script.string:
                import re
                match = re.search(r'window\.flightinfo\s*=\s*({.*?});', script.string, re.DOTALL)
                if match:
                    try:
                        js_data = match.group(1)
                        js_data = js_data.replace('true', 'True').replace('false', 'False')
                        flight_info_data = eval(js_data)
                    except:
                        continue
        
        modal_spans = self.soup.find_all('span', class_='modal-top-right-text')
        for span in modal_spans:
            full_tariff_class = span.get_text(strip=True) 
            parts = full_tariff_class.strip().split()
            if len(parts) < 2:
                continue
            tariff_type = parts[0]
            class_letter = parts[1].upper()
            
            if tariff_type.lower() != 'iqtisodiy':
                continue
            if class_letter not in [c.upper() for c in self.class_name]:
                continue
                
            modal_window = span.find_parent('div', class_='modal-window')
            if not modal_window:
                continue
            modal_id = modal_window.get('id', '')
            if not modal_id.startswith('penalty'):
                continue
            tariff_id = modal_id.replace('penalty', '')
            
            refund_fee = 'Noma\'lum'
            refund_currency = 'UZS'
            features = modal_window.find_all('div', class_='tariff-feature')
            for feature in features:
                feature_text = feature.get_text(strip=True)
                if 'Aviachiptani qaytarish' in feature_text and 'keyin' not in feature_text:
                    next_div = feature.find_next_sibling('div', class_='tariff-feature-details')
                    if next_div:
                        fee_text = next_div.get_text(strip=True)
                        fee_match = re.search(r'(\d[\d\s]*)\s*(UZS|USD)', fee_text)
                        if fee_match:
                            refund_fee = fee_match.group(1).replace(" ", "")
                            refund_currency = fee_match.group(2)
                            break
                        elif 'ushlab qolinadi' in fee_text or 'qaytarilmaydi' in fee_text:
                            refund_fee = 'Qaytarilmaydi'
                            break
            
            for col in self.soup.find_all('div', class_='tariff-col'):
                link = col.find('a', href=lambda x: x and tariff_id in x)
                if not link:
                    continue
                    
                col_classes = col.get('class', [])
                flight_code = next((cls for cls in col_classes if cls in flight_map), None)
                if not flight_code:
                    continue
                    
                selected_flight_number = flight_map[flight_code]
                if flight_number and selected_flight_number != flight_number:
                    continue
                    
                features = col.find_all('div', class_='tariff-feature')
                has_refund = any("Qaytarish bilan" in f.get_text(strip=True) for f in features)
                if not has_refund:
                    continue
                    
                price_div = col.find('div', class_='tariff-price')
                if not price_div:
                    continue
                price_text = price_div.get_text(strip=True)
                price_match = re.search(r'(\d[\d\s]*)', price_text)
                if not price_match:
                    continue
                price = price_match.group(1).replace(" ", "")
                currency_div = price_div.find('div', class_='price-currency')
                currency = currency_div.get_text(strip=True) if currency_div else 'UZS'
                
                seat_span = col.find('span', class_='tariff-left-places')
                seats = seat_span.get_text(strip=True) if seat_span else 'Nomaʼlum'
                
                js_flight_data = flight_info_data.get(flight_code, {}).get('OW', {})
                
                result = {
                    'route': f"{self.flight_info.get('from')} -> {self.flight_info.get('to')}",
                    'flight_number': selected_flight_number,
                    'departure_time': self.flight_info.get('departure_time'),
                    'arrival_time': self.flight_info.get('arrival_time'),
                    'date': self.flight_info.get('departure_date'),
                    'airplane': self.flight_info.get('airplane'),
                    'tariff_type': tariff_type,
                    'tariff_class': class_letter,
                    'price': price,
                    'currency': currency,
                    'available_seats': seats,
                    'refund_fee': refund_fee,
                    'refund_currency': refund_currency
                }
                if js_flight_data:
                    result.update({
                        'route': f"{js_flight_data.get('from_name', result['route'].split(' -> ')[0])} -> {js_flight_data.get('to_name', result['route'].split(' -> ')[1])}",
                        'departure_time': js_flight_data.get('deptime', result['departure_time']),
                        'arrival_time': js_flight_data.get('arrtime', result['arrival_time']),
                        'date': js_flight_data.get('depdate', result['date']),
                        'airplane': js_flight_data.get('board_name', result['airplane'])
                    })
                
                results.append(result)
        
        return results
    
    def get_flights_list(self):
        """Berilgan sanadagi barcha reyslarni qaytaradi"""
        flights = []
        try:
            flight_time_area = self.soup.find('div', id='OWtime_form')
            if flight_time_area:
                labels = flight_time_area.find_all('label')
                for label in labels:
                    span = label.find('span', class_='value')
                    if span:
                        flight_data = {
                            'flight_number': span.find('span', class_='flight-data').get_text(strip=True),
                            'departure_time': span.get_text(strip=True).split()[0]
                        }
                        flights.append(flight_data)

            flight_time_area2 = self.soup.find('div', id='OW2time_form')
            if flight_time_area2 and flight_time_area2.text.strip():
                labels = flight_time_area2.find_all('label')
                for label in labels:
                    span = label.find('span', class_='value')
                    if span:
                        flight_data = {
                            'flight_number': span.find('span', class_='flight-data').get_text(strip=True),
                            'departure_time': span.get_text(strip=True).split()[0]
                        }
                        flights.append(flight_data)

        except Exception as e:
            print(f"[Xatolik] Reyslar ro'yxatini olishda: {e}")
            return []
        return flights

    async def find_missing_classes(self):
        if not await self.load_file():
            return False
        all_economy_classes = set("B C D I K L M O P R S T U V Y".split())
        found_classes_by_flight = defaultdict(set)

        script = self.soup.find('script', string=re.compile(r'window\.flightinfo\s*=\s*{'))
        if not script:
            raise ValueError("⚠️ window.flightinfo boshlanmayapti!")

        flight_number_map = {}  
        for match in re.finditer(r'"(\d{6})":\s*{\s*"OW":\s*{[^}]*?"flight":"(\d+)"', script.string):
            html_key, flight_number = match.groups()
            flight_number_map[html_key] = flight_number

        if not flight_number_map:
            raise ValueError("⚠️ window.flightinfo JSON parchasi ajratilmadi!")

        for tariff_block in self.soup.select('div.tariff-col'):
            class_list = tariff_block.get('class', [])
            html_key = next((cls for cls in class_list if cls.isdigit()), None)
            if not html_key or html_key not in flight_number_map:
                continue

            flight_number = flight_number_map[html_key]

            fines_btn = tariff_block.select_one('.tariff-fines')
            if not fines_btn:
                continue

            onclick = fines_btn.get('onclick', '')
            match = re.search(r"showpenaltymodal\('([^']+)'\)", onclick)
            if not match:
                continue

            modal_id = f'penalty{match.group(1)}'
            modal = self.soup.find('div', id=modal_id)
            if not modal:
                continue

            span = modal.find('span', class_='modal-top-right-text')
            if not span:
                continue

            text = span.get_text(strip=True)
            if text.lower().startswith('iqtisodiy'):
                parts = text.split()
                if len(parts) > 1:
                    class_code = parts[-1]
                    if class_code in all_economy_classes:
                        found_classes_by_flight[flight_number].add(class_code)

        missing_by_flight = {}
        for html_key, flight_number in flight_number_map.items():
            found = found_classes_by_flight.get(flight_number, set())
            missing = all_economy_classes - found
            missing_by_flight[flight_number] = sorted(missing)
        if self.file_path and os.path.exists(self.file_path):
            os.remove(self.file_path)

        return missing_by_flight


    
    async def run(self, class_name: str, flight_number: str = None) -> list:
        self.class_name = class_name
        load = await self.load_file()
        if not load:
            return False

        flight_info = self.extract_flight_info()
        if not flight_info:
            return False

        results = self.parse_tariffs(flight_number=flight_number)
        return results

if __name__ == '__main__':
    import asyncio
    async def main():
        parser = FlightParser(
            from_city='TAS',
            to_city='UGC',
            date='2025-09-10',
        )
        missing = await parser.find_missing_classes()
        print(missing)
        # result = await (parser.run(class_name=["M", "O"]))
        # print(result)
        # with open('result.json', 'w', encoding='utf-8') as f:
        #     json.dump(result, f, ensure_ascii=False, indent=4)
    asyncio.run(main())