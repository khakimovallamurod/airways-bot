from bs4 import BeautifulSoup
import re
import json
import config
import os
from playwright.async_api import async_playwright
from datetime import datetime
import hashlib

class FlightParser:
    all_possible_classes = {'R', 'P', 'L', 'U', 'S', 'O', 'V', 'T', 'K', 'M', 'B', 'Y', 'I', 'D', 'C'}

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
            browser = await p.chromium.launch(headless=False)
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
        if not await self.load_browser():
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

                results.append({
                    'route': f"{self.flight_info.get('from')} -> {self.flight_info.get('to')}",
                    'flight_number': flight_number,
                    'departure_time': self.flight_info.get('departure_time'),
                    'arrival_time': self.flight_info.get('arrival_time'),
                    'date': self.flight_info.get('departure_date'),
                    'airplane': self.flight_info.get('airplane'),
                    'tariff_type': tariff_type,
                    'tariff_class': class_letter,
                    'price': price,
                    'currency': currency,
                    'available_seats': seats
                })

        if self.file_path and os.path.exists(self.file_path):
            os.remove(self.file_path)
        print(results)
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
    
    async def find_missing_classes(self) -> dict:
        """Har bir reys uchun yo'qolgan klasslarni aniqlaydi"""
        if not await self.load_file():
            return {}

        flights = self.get_flights_list()
        missing_classes_dict = {}

        for flight in flights:
            flight_number = flight['flight_number']  
            found_classes = set()

            spans = self.soup.find_all('span', class_='modal-top-right-text')
            for span in spans:
                text = span.get_text(strip=True)
                parts = text.split()
                if len(parts) >= 2:
                    class_letter = parts[-1]
                    if class_letter in self.all_possible_classes:
                        found_classes.add(class_letter)

            missing = sorted(self.all_possible_classes - found_classes)
            missing_classes_dict[flight_number] = missing

        return missing_classes_dict
    
    async def run(self, class_name: str, flight_number: str = None) -> list:
        self.class_name = class_name
        if not await self.load_file():
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
            date='2025-08-01',
        )
        # missing = await parser.find_missing_classes()
        # print(missing)
        result = await (parser.run(class_name=["M", "O"]))
        print(result)
        with open('result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
    asyncio.run(main())