from bs4 import BeautifulSoup
import re
import json
import config
import os
from playwright.async_api import async_playwright
from datetime import datetime
import hashlib
from collections import defaultdict
import asyncio

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

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.page = await self.browser.new_page()

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
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
            await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=60000)
            await asyncio.sleep(2)
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
        """Extract flight information for both single and multi-segment flights"""
        try:
            segments = []
            
            segment_ids = ['segmentfirst', 'segmentsecond', 'segmentthird', 'segmentfourth']
            for segment_id in segment_ids:
                ticket = self.soup.find('div', class_='booking-ticket-item', id=segment_id)
                if ticket and ticket.find('div', class_='booking-ticket-item-number flight'):
                    flight_number_elem = ticket.find('div', class_='booking-ticket-item-number flight')
                    flight_number = flight_number_elem.get_text(strip=True)
                    
                    if not flight_number or flight_number == 'HY':
                        continue
                    
                    direction_elem = ticket.find('div', class_='booking-ticket-item-direction fromto_name')
                    spans = direction_elem.find_all('span') if direction_elem else []
                    
                    if len(spans) >= 2:
                        segment_info = {
                            'segment_id': segment_id,
                            'flight_number': flight_number,
                            'from': spans[0].get_text(strip=True),
                            'to': spans[1].get_text(strip=True),
                            'departure_time': ticket.find('div', class_='booking-ticket-item-time deptime').get_text(strip=True) if ticket.find('div', class_='booking-ticket-item-time deptime') else '',
                            'arrival_time': ticket.find('div', class_='booking-ticket-item-time text-right arrtime').get_text(strip=True) if ticket.find('div', class_='booking-ticket-item-time text-right arrtime') else '',
                            'departure_date': ticket.find('div', class_='booking-ticket-item-date depdate').get_text(separator=' ', strip=True) if ticket.find('div', class_='booking-ticket-item-date depdate') else '',
                            'arrival_date': ticket.find('div', class_='booking-ticket-item-date text-right arrdate').get_text(separator=' ', strip=True) if ticket.find('div', class_='booking-ticket-item-date text-right arrdate') else '',
                            'airplane': ticket.find('div', class_='booking-ticket-item-flight-airplane board').get_text(strip=True) if ticket.find('div', class_='booking-ticket-item-flight-airplane board') else ''
                        }
                        segments.append(segment_info)
            
            if segments:
                self.flight_info = {
                    'segments': segments,
                    'is_multi_segment': len(segments) > 1,
                    'total_segments': len(segments),
                    'route': ' -> '.join([seg['from'] for seg in segments] + [segments[-1]['to']]) if segments else '',
                    'first_departure_time': segments[0]['departure_time'] if segments else '',
                    'last_arrival_time': segments[-1]['arrival_time'] if segments else '',
                    'departure_date': segments[0]['departure_date'] if segments else '',
                    'arrival_date': segments[-1]['arrival_date'] if segments else ''
                }
                
                if len(segments) == 1:
                    seg = segments[0]
                    self.flight_info.update({
                        'flight_number': seg['flight_number'],
                        'from': seg['from'],
                        'to': seg['to'],
                        'departure_time': seg['departure_time'],
                        'arrival_time': seg['arrival_time'],
                        'airplane': seg['airplane']
                    })
                else:
                    flight_numbers = [seg['flight_number'] for seg in segments]
                    self.flight_info['flight_number'] = ' + '.join(flight_numbers)
                    self.flight_info['from'] = segments[0]['from']
                    self.flight_info['to'] = segments[-1]['to']
                    self.flight_info['departure_time'] = segments[0]['departure_time']
                    self.flight_info['arrival_time'] = segments[-1]['arrival_time']
                    self.flight_info['airplane'] = ', '.join([seg['airplane'] for seg in segments if seg['airplane']])
            
            return self.flight_info

        except Exception as e:
            print(f"[Xatolik] Reys ma'lumotlarini olishda: {e}")
            return {}

    def parse_tariffs(self, flight_number=None):
        """Parse tariffs for both one-way and round-trip flights"""
        results = []
        flight_map = {}
        
        time_form_selectors = ['#OWtime_form .timeowglobalclass', '#RTtime_form .timeowglobalclass']
        for selector in time_form_selectors:
            for span in self.soup.select(selector):
                code = span.get('data-time')
                flight_data_span = span.find('span', class_='flight-data')
                if flight_data_span:
                    flight_text = flight_data_span.get_text(strip=True)
                    flight_map[code] = flight_text
        
        flight_info_data = {}
        script_tags = self.soup.find_all('script')
        for script in script_tags:
            if script.string and 'window.flightinfo' in script.string:
                match = re.search(r'window\.flightinfo\s*=\s*({.*?});', script.string, re.DOTALL)
                if match:
                    try:
                        js_data = match.group(1)
                        js_data = js_data.replace('true', 'True').replace('false', 'False')
                        flight_info_data = eval(js_data)
                    except Exception as e:
                        print(f"Warning: Could not parse flight info data: {e}")
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
            if self.class_name and class_letter not in [c.upper() for c in self.class_name]:
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
            is_refundable = False
            
            features = modal_window.find_all('div', class_='tariff-feature')
            for feature in features:
                feature_text = feature.get_text(strip=True)
                
                if 'Aviachiptani qaytarish' in feature_text and 'keyin' not in feature_text:
                    next_div = feature.find_next_sibling('div', class_='tariff-feature-details')
                    if next_div:
                        fee_text = next_div.get_text(strip=True)
                        
                        if 'ushlab qolinadi' in fee_text or 'qaytarilmaydi' in fee_text:
                            red_span = next_div.find('span', style=lambda x: x and 'color:red' in x)
                            if red_span:
                                refund_fee = 'Qaytarilmaydi'
                                is_refundable = False
                            else:
                                fee_match = re.search(r'(\d+(?:[\s\d]*\d)?)\s*(UZS|USD)', fee_text)
                                if fee_match:
                                    refund_fee = fee_match.group(1).replace(" ", "")
                                    refund_currency = fee_match.group(2)
                                    is_refundable = True
                        else:
                            fee_match = re.search(r'(\d+(?:[\s\d]*\d)?)\s*(UZS|USD)', fee_text)
                            if fee_match:
                                refund_fee = fee_match.group(1).replace(" ", "")
                                refund_currency = fee_match.group(2)
                                is_refundable = True
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
                
                price_div = col.find('div', class_='tariff-price')
                if not price_div:
                    continue
                
                price_text = ""
                for child in price_div.children:
                    if hasattr(child, 'get') and child.get('class'):
                        if 'price-desc' in child.get('class') or 'price-currency' in child.get('class'):
                            continue
                    elif hasattr(child, 'name') and child.name == 'button':
                        continue
                    elif hasattr(child, 'string') and child.string:
                        text = child.string.strip()
                        if re.match(r'^\d[\d\s]*$', text):
                            price_text = text
                            break
                
                if not price_text:
                    all_text = price_div.get_text(strip=True)
                    price_match = re.search(r'yo\'lovchi uchun\s+(\d{1,3}(?:\s\d{3})*)', all_text)
                    if price_match:
                        price_text = price_match.group(1)
                    else:
                        price_match = re.search(r'(\d{1,3}(?:\s\d{3})*)', all_text)
                        if price_match:
                            price_text = price_match.group(1)
                
                if not price_text:
                    continue
                
                price = price_text.replace(" ", "")
                currency_div = price_div.find('div', class_='price-currency')
                currency = currency_div.get_text(strip=True) if currency_div else 'UZS'
                
                seat_span = col.find('span', class_='tariff-left-places')
                seats = seat_span.get_text(strip=True) if seat_span else 'Nomaʼlum'
                
                flight_data_dict = flight_info_data.get(flight_code, {})
                
                directions = []
                if 'OW' in flight_data_dict:
                    directions.append(('OW', 'outbound'))
                if 'RT' in flight_data_dict:
                    directions.append(('RT', 'return'))
                
                if not directions:
                    directions = [('OW', 'outbound')]
                
                for direction_key, direction_name in directions:
                    js_flight_data = flight_data_dict.get(direction_key, [])
                    if is_refundable != True:
                        continue
                    if isinstance(js_flight_data, list) and js_flight_data:
                        first_segment = js_flight_data[0]
                        last_segment = js_flight_data[-1] if len(js_flight_data) > 1 else first_segment
                        
                        route_parts = []
                        for seg in js_flight_data:
                            if seg.get('from_name') not in route_parts:
                                route_parts.append(seg.get('from_name', ''))
                        route_parts.append(last_segment.get('to_name', ''))
                        route = ' -> '.join(filter(None, route_parts))
                        
                        flight_numbers = [seg.get('flight', '') for seg in js_flight_data]
                        combined_flight_number = ' + '.join(filter(None, flight_numbers))
                        
                        result = {
                            'direction': direction_name,
                            'direction_code': direction_key,
                            'route': route,
                            'flight_number': combined_flight_number,
                            'departure_time': first_segment.get('deptime', ''),
                            'arrival_time': last_segment.get('arrtime', ''),
                            'date': first_segment.get('depdate', ''),
                            'airplane': ', '.join([seg.get('board_name', '') for seg in js_flight_data if seg.get('board_name')]),
                            'tariff_type': tariff_type,
                            'tariff_class': class_letter,
                            'price': price,
                            'currency': currency,
                            'available_seats': seats,
                            'refund_fee': refund_fee,
                            'refund_currency': refund_currency,
                            'is_refundable': is_refundable,
                            'is_multi_segment': len(js_flight_data) > 1,
                            'total_segments': len(js_flight_data),
                            'segments': []
                        }
                        
                        for i, seg in enumerate(js_flight_data):
                            segment_info = {
                                'segment_number': i + 1,
                                'flight_number': f"HY {seg.get('flight', '')}",
                                'from': seg.get('from_name', ''),
                                'to': seg.get('to_name', ''),
                                'departure_time': seg.get('deptime', ''),
                                'arrival_time': seg.get('arrtime', ''),
                                'date': seg.get('depdate', ''),
                                'airplane': seg.get('board_name', ''),
                                'duration': seg.get('duration_text', '')
                            }
                            result['segments'].append(segment_info)
                            
                    elif isinstance(js_flight_data, dict):
                        result = {
                            'direction': direction_name,
                            'direction_code': direction_key,
                            'route': f"{js_flight_data.get('from_name', self.from_city)} -> {js_flight_data.get('to_name', self.to_city)}",
                            'flight_number': js_flight_data.get('flight', selected_flight_number),
                            'departure_time': js_flight_data.get('deptime', ''),
                            'arrival_time': js_flight_data.get('arrtime', ''),
                            'date': js_flight_data.get('depdate', ''),
                            'airplane': js_flight_data.get('board_name', ''),
                            'tariff_type': tariff_type,
                            'tariff_class': class_letter,
                            'price': price,
                            'currency': currency,
                            'available_seats': seats,
                            'refund_fee': refund_fee,
                            'refund_currency': refund_currency,
                            'is_refundable': is_refundable,
                            'is_multi_segment': False,
                            'total_segments': 1,
                            'segments': []
                        }
                    else:
                        result = {
                            'direction': direction_name,
                            'direction_code': direction_key,
                            'route': self.flight_info.get('route', f"{self.from_city} -> {self.to_city}"),
                            'flight_number': selected_flight_number,
                            'departure_time': self.flight_info.get('first_departure_time', ''),
                            'arrival_time': self.flight_info.get('last_arrival_time', ''),
                            'date': self.flight_info.get('departure_date', ''),
                            'airplane': self.flight_info.get('airplane', ''),
                            'tariff_type': tariff_type,
                            'tariff_class': class_letter,
                            'price': price,
                            'currency': currency,
                            'available_seats': seats,
                            'refund_fee': refund_fee,
                            'refund_currency': refund_currency,
                            'is_refundable': is_refundable,
                            'is_multi_segment': self.flight_info.get('is_multi_segment', False),
                            'total_segments': self.flight_info.get('total_segments', 1),
                            'segments': []
                        }
                    
                    results.append(result)
        
        return results
    
    def get_flights_list(self):
        """Get list of all available flights for both directions"""
        flights = []
        try:
            flight_time_areas = [
                ('#OWtime_form', 'outbound'),
                ('#OW2time_form', 'outbound_segment2'), 
                ('#RTtime_form', 'return'),
                ('#RT2time_form', 'return_segment2')
            ]
            
            for area_id, direction in flight_time_areas:
                flight_time_area = self.soup.select_one(area_id)
                if flight_time_area and flight_time_area.get_text(strip=True):
                    labels = flight_time_area.find_all('label')
                    for label in labels:
                        span = label.find('span', class_='value')
                        if span:
                            flight_data_span = span.find('span', class_='flight-data')
                            if flight_data_span:
                                flight_data = {
                                    'direction': direction,
                                    'flight_number': flight_data_span.get_text(strip=True),
                                    'departure_time': span.get_text(strip=True).split()[0],
                                    'data_time': span.get('data-time', ''),
                                    'data_key': span.get('data-key', '')
                                }
                                flights.append(flight_data)

        except Exception as e:
            print(f"[Xatolik] Reyslar ro'yxatini olishda: {e}")
            return []
        
        return flights

    async def find_missing_classes(self):
        """Find missing booking classes for each flight (both directions)"""
        if not await self.load_file():
            return False
        
        all_economy_classes = set("B C D I K L M O P R S T U V Y".split())
        found_classes_by_flight = defaultdict(lambda: {'OW': set(), 'RT': set()})

        script = self.soup.find('script', string=re.compile(r'window\.flightinfo\s*=\s*{'))
        if not script:
            return {}

        flight_number_map = {}
        
        match = re.search(r'window\.flightinfo\s*=\s*({.*?});', script.string, re.DOTALL)
        if match:
            try:
                js_data = match.group(1)
                js_data = js_data.replace('true', 'True').replace('false', 'False')
                flight_info_data = eval(js_data)
                
                for html_key, flight_data in flight_info_data.items():
                    directions = {}
                    
                    if 'OW' in flight_data:
                        ow_data = flight_data['OW']
                        if isinstance(ow_data, list) and ow_data:
                            flight_numbers = [seg.get('flight', '') for seg in ow_data if seg.get('flight')]
                            if flight_numbers:
                                directions['OW'] = ' + '.join(flight_numbers)
                        elif isinstance(ow_data, dict):
                            ow_flight = ow_data.get('flight', '')
                            if ow_flight:
                                directions['OW'] = ow_flight
                                
                    if 'RT' in flight_data:
                        rt_data = flight_data['RT']
                        if isinstance(rt_data, list) and rt_data:
                            flight_numbers = [seg.get('flight', '') for seg in rt_data if seg.get('flight')]
                            if flight_numbers:
                                directions['RT'] = ' + '.join(flight_numbers)
                        elif isinstance(rt_data, dict):
                            rt_flight = rt_data.get('flight', '')
                            if rt_flight:
                                directions['RT'] = rt_flight
                    
                    if directions:
                        flight_number_map[html_key] = directions
                            
            except Exception as e:
                print(f"Error parsing JavaScript data: {e}")

        if not flight_number_map:
            raise ValueError("⚠️ No flight numbers found in JavaScript data!")

        for tariff_block in self.soup.select('div.tariff-col'):
            class_list = tariff_block.get('class', [])
            html_key = next((cls for cls in class_list if cls in flight_number_map), None)
            if not html_key:
                continue

            flight_directions = flight_number_map[html_key]

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
                    class_code = parts[1].upper()  
                    if class_code in all_economy_classes:
                        for direction, flight_number in flight_directions.items():
                            found_classes_by_flight[flight_number][direction].add(class_code)

        missing_by_flight = {}
        for html_key, flight_directions in flight_number_map.items():
            for direction, flight_number in flight_directions.items():
                flight_key = f"{flight_number}"
                found = found_classes_by_flight.get(flight_number, {}).get(direction, set())
                missing = all_economy_classes - found
                missing_by_flight[flight_key] = sorted(missing)
        
        return missing_by_flight

    async def run(self, class_name: list, flight_number: str = None) -> list:
        """Main method to run the parser"""
        self.class_name = class_name
        load = await self.load_file()
        if not load:
            return False

        flight_info = self.extract_flight_info()
        if not flight_info:
            print("No flight info extracted")
            return False

        results = self.parse_tariffs(flight_number=flight_number)
        
        return results

if __name__ == '__main__':
    import asyncio
    
    async def main():
        parser = FlightParser(
            from_city='TAS',
            to_city='UGC',
            date='2025-09-28',
        )
        
        print("Testing multi-segment route:")
        result = await parser.run(class_name=["M", "O"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Test finding missing classes
        print("\nFinding missing classes:")
        missing = await parser.find_missing_classes()
        print(missing)

    asyncio.run(main())