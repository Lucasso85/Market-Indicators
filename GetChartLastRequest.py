import socket
import ssl
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import glob
import threading
import logging
from logging.handlers import TimedRotatingFileHandler

# Zaktualizowana klasa Logger
class Logger:
    loggers = {}
    
    @staticmethod
    def get_logger(name):
        if name in Logger.loggers:
            return Logger.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        if logger.hasHandlers():
            logger.handlers.clear()
        
        log_file = os.path.join('logs', f"{name}.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
        handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1)
        handler.setLevel(logging.INFO)
            
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
            
        logger.addHandler(handler)

        Logger.loggers[name] = logger
        return logger

# Przykładowe użycie loggera w głównym pliku kodu
logger = Logger.get_logger('GetChartLastRequest')

# Ustawienia plików stanu
state_instruments_filename = 'selected_instruments.json'
state_periods_filename = 'selected_periods.json'
DATA_FOLDER = 'C:/Users/lukas/Desktop/Projekty PY/DASH_project/LastRequest_data'

# Funkcja do wczytywania stanu wybranych instrumentów
def load_selected_instruments():
    if os.path.exists(state_instruments_filename):
        with open(state_instruments_filename, 'r') as f:
            return json.load(f)
    return []

# Funkcja do wczytywania wybranych okresów
def load_selected_periods():
    if os.path.exists(state_periods_filename):
        with open(state_periods_filename, 'r') as f:
            return json.load(f)
    return []

def create_ssl_socket(host, port):
    """Tworzenie połączenia SSL"""
    logger.info("Tworzenie połączenia SSL")
    host_ip = socket.getaddrinfo(host, port)[0][4][0]
    sock = socket.create_connection((host_ip, port))
    context = ssl.create_default_context()
    return context.wrap_socket(sock, server_hostname=host)

def send_request(sock, parameters):
    """Wysyłanie zapytania do serwera i odbieranie odpowiedzi"""
    logger.info("Wysyłanie zapytania")
    END = b'\n\n'
    packet = json.dumps(parameters).encode('UTF-8')
    sock.send(packet)
    
    response = b""
    while True:
        part = sock.recv(16384)
        response += part
        if END in part:
            break
    return response[:response.find(END)].decode('UTF-8') if END in response else None

def remove_old_files(folder_path, symbol, period):
    """Usuwanie starych plików CSV dla danego symbolu i okresu"""
    pattern = os.path.join(folder_path, f"{symbol.lower()}_{period}min_*.csv")
    old_files = glob.glob(pattern)
    for old_file in old_files:
        os.remove(old_file)
        logger.info(f"Usunięto stary plik: {old_file}")

def save_to_csv(dataframe, symbol, period):
    """Zapisywanie danych do pliku CSV"""
    folder_path = DATA_FOLDER
    os.makedirs(folder_path, exist_ok=True)
    
    # Usuwanie starych plików
    remove_old_files(folder_path, symbol, period)
    
    # Sortowanie danych według znacznika czasu
    dataframe = dataframe.sort_values(by='timestamp', ascending=False)
    
    # Tworzenie nazwy pliku i zapisywanie danych
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"{symbol.lower()}_{period}min_{date_str}.csv"
    full_path = os.path.join(folder_path, file_name)
    dataframe.to_csv(full_path, index=False)
    logger.info(f"Dane zapisane do pliku {full_path}")

def fetch_data(sock, symbol, period, userid, password):
    """Pobieranie danych wykresu dla danego symbolu i okresu"""
    start_time = int((datetime.now() - timedelta(days=40)).timestamp() * 1000)

    get_chart_last_parameters = {
        "command": "getChartLastRequest",
        "arguments": {
            "info": {
                "symbol": symbol,
                "period": period,
                "start": start_time
            }
        }
    }
    logger.info(f'Wysyłanie getChartLastRequest dla {symbol}, okres {period}...')
    chart_response = send_request(sock, get_chart_last_parameters)
    if not chart_response:
        logger.error(f'Brak odpowiedzi dla getChartLastRequest dla {symbol}, okres {period}')
        return

    chart_data = json.loads(chart_response)
    logger.info(f'Otrzymano dane wykresu dla {symbol}, okres {period}')

    if not chart_data['status'] or 'rateInfos' not in chart_data['returnData']:
        logger.error(f'Błąd w odpowiedzi dla {symbol}, okres {period}: {chart_data}')
        return

    rate_infos = chart_data['returnData']['rateInfos']
    digits = chart_data['returnData']['digits']
    logger.info(f"Otrzymano {len(rate_infos)} punktów danych dla {symbol}, okres {period}.")

    # Przetwarzanie danych na odpowiedni format
    factor = 10 ** digits
    data = [
        {
            "timestamp": datetime.fromtimestamp(item['ctm'] / 1000),
            "open": item['open'] / factor,
            "close": (item['open'] + item['close']) / factor,
            "high": (item['open'] +item['high']) / factor,
            "low": (item['open'] +item['low']) / factor,
            "vol":  item['vol'] ,
            "INSTRUMENT": symbol
        } for item in rate_infos
    ]
    df = pd.DataFrame(data)
    
    save_to_csv(df, symbol, period)

def fetch_all_data(instruments, periods):
    """Pobieranie danych dla wszystkich wybranych instrumentów i okresów"""
    host = 'xapi.xtb.com'
    port = 5112 #Real port
    USERID =  2812673  # Real Login 
    PASSWORD = 'Levistrauss851!' # Real Password
    # host = 'xapia.x-station.eu'
    # port = 5124
    # USERID = 16237362
    # PASSWORD = 'xoh12773'

    with create_ssl_socket(host, port) as sock:
        # Logowanie do API
        login_parameters = {"command": "login", "arguments": {"userId": USERID, "password": PASSWORD}}
        login_response = send_request(sock, login_parameters)
        if not login_response:
            logger.error('Logowanie nie powiodło się')
            return

        logger.info('Login response: ' + login_response)

        for symbol in instruments:
            for period in periods:
                fetch_data(sock, symbol, period, USERID, PASSWORD)
                time.sleep(1)  # Mała przerwa między zapytaniami

        # Wylogowanie z API
        logout_parameters = {"command": "logout"}
        logout_response = send_request(sock, logout_parameters)
        logger.info('Logout response: ' + logout_response)

def main():
    """Główna funkcja skryptu"""
    selected_instruments = load_selected_instruments()
    selected_periods = load_selected_periods()
    
    if not selected_instruments:
        logger.error("Brak wybranych instrumentów. Proszę uruchomić skrypt wyboru instrumentów.")
        return

    if not selected_periods:
        logger.error("Brak wybranych okresów. Proszę uruchomić skrypt wyboru okresów.")
        return

    threading.Thread(target=fetch_all_data, args=(selected_instruments, selected_periods)).start()

if __name__ == '__main__':
    logger.info("Rozpoczęcie skryptu GetChartLastRequest")
    main()
