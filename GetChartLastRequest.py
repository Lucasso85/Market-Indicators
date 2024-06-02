import socket
import ssl
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import glob
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

# Ustawienia logowania
log_folder = 'logs'
os.makedirs(log_folder, exist_ok=True)
log_filename = os.path.join(log_folder, 'GetChartLastRequest.log')
state_filename = 'selected_instruments.json'  # Plik do zapisywania stanu wybranych instrumentów

# Konfiguracja loggera
logger = logging.getLogger('GetChartLastRequest')
logger.setLevel(logging.INFO)

# Tworzenie handlera do pliku
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)

# Tworzenie handlera do konsoli
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatowanie logów
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Dodanie handlerów do loggera
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Funkcja do wczytywania listy instrumentów z pliku
def load_instruments(file_path='instruments.txt'):
    """Wczytywanie listy instrumentów z pliku tekstowego"""
    instruments = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 2:
                instruments.append((parts[0], parts[1]))
    return instruments

# Funkcja do zapisywania stanu wybranych instrumentów
def save_selected_instruments(selected_instruments):
    with open(state_filename, 'w') as f:
        json.dump(selected_instruments, f)

# Funkcja do wczytywania stanu wybranych instrumentów
def load_selected_instruments():
    if os.path.exists(state_filename):
        with open(state_filename, 'r') as f:
            return json.load(f)
    return []

# Lista dostępnych instrumentów
ALL_INSTRUMENTS = load_instruments()

PERIODS = [5, 15, 60]
DATA_FOLDER = 'C:/Users/lukas/Desktop/Projekty PY/API dane gieldowe/LastRequest_data'

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
    start_time = int((datetime.now() - timedelta(days=20)).timestamp() * 1000)

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
            "high": item['high'] / factor,
            "low": item['low'] / factor,
            "vol": item['vol'],
            "INSTRUMENT": symbol
        } for item in rate_infos
    ]
    df = pd.DataFrame(data)
    
    logger.info(str(df))
    
    save_to_csv(df, symbol, period)

def main():
    """Główna funkcja skryptu"""
    def on_start():
        """Obsługa przycisku start"""
        selected_instruments = [instr for instr, var in instruments_vars.items() if var.get()]
        if not selected_instruments:
            messagebox.showwarning("Brak wyboru", "Proszę wybrać co najmniej jeden instrument.")
            return

        # Zapisanie wybranego stanu do pliku
        save_selected_instruments(selected_instruments)
        
        threading.Thread(target=fetch_all_data, args=(selected_instruments, PERIODS)).start()

    def fetch_all_data(instruments, periods):
        """Pobieranie danych dla wszystkich wybranych instrumentów i okresów"""
        host = 'xapia.x-station.eu'
        port = 5124
        USERID = 16237362
        PASSWORD = 'xoh12773'

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

    # Interfejs użytkownika
    root = tk.Tk()
    root.title("Wybór instrumentów")

    # Wczytywanie poprzedniego stanu wybranych instrumentów
    previous_selected_instruments = load_selected_instruments()

    # Tworzenie pól wyboru dla instrumentów w formie tabeli
    instruments_vars = {}
    num_rows = 15
    num_cols = (len(ALL_INSTRUMENTS) + num_rows - 1) // num_rows  # Obliczanie liczby kolumn

    table_frame = ttk.Frame(root)
    table_frame.pack()

    for col in range(num_cols):
        for row in range(num_rows):
            index = col * num_rows + row
            if index < len(ALL_INSTRUMENTS):
                symbol, description = ALL_INSTRUMENTS[index]
                var = tk.BooleanVar(value=symbol in previous_selected_instruments)
                chk = ttk.Checkbutton(table_frame, text=f"{symbol} - {description}", variable=var)
                chk.grid(row=row, column=col, sticky='w')
                instruments_vars[symbol] = var

    # Przycisk start
    btn_start = ttk.Button(root, text="Start", command=on_start)
    btn_start.pack(pady=10)

    # Uruchomienie interfejsu użytkownika
    root.mainloop()

if __name__ == '__main__':
    logger.info("Rozpoczęcie skryptu GetChartLastRequest")
    main()
