import socket
import ssl
import json
import pandas as pd
from datetime import datetime
import os
import glob
import logging

# Ustawienia logowania
log_folder = 'logs'
os.makedirs(log_folder, exist_ok=True)
log_filename = os.path.join(log_folder, 'GetAllSymbols.log')

# Konfiguracja loggera
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Usunięcie istniejących handlerów, aby uniknąć podwójnych logów
if logger.hasHandlers():
    logger.handlers.clear()

# FileHandler - zapisywanie logów do pliku
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# StreamHandler - wyświetlanie logów w konsoli
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

def create_ssl_socket(host, port):
    """Tworzenie połączenia SSL"""
    logger.info("Tworzenie połączenia SSL")
    host_ip = socket.getaddrinfo(host, port)[0][4][0]
    sock = socket.create_connection((host_ip, port))
    context = ssl.create_default_context()
    return context.wrap_socket(sock, server_hostname=host)

def send_request(sock, parameters):
    """Wysyłanie zapytania i odbieranie odpowiedzi"""
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

def save_to_csv(dataframe, folder_path='C:/Users/lukas/Desktop/Projekty PY/DASH_project/ALL_Symbols_data'):
    """Zapisywanie danych do pliku CSV i usuwanie starych plików"""
    logger.info("Zapisywanie danych do CSV")
    os.makedirs(folder_path, exist_ok=True)
    
    # Zapis nowego pliku
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f"symbols_{date_str}.csv"
    full_path = os.path.join(folder_path, file_name)
    dataframe.to_csv(full_path, index=False)
    logger.info(f"Dane zapisane do pliku {full_path}")

    # Usunięcie starych plików, zachowanie tylko 20 ostatnich
    files = sorted(glob.glob(os.path.join(folder_path, "symbols_*.csv")), key=os.path.getmtime, reverse=True)
    for old_file in files[20:]:
        os.remove(old_file)
        logger.info(f"Usunięto stary plik: {old_file}")

def main():
    """Główna funkcja skryptu"""
    logger.info("Rozpoczęcie skryptu GetAllSymbols")
    host = 'xapi.xtb.com'
    port = 5112 #Real port
    USERID =  2812673  # Real Login 
    PASSWORD = 'Levistrauss851!' # Real Password
    # port = 5124 # demo 
    # USERID = 16237362 # demo 
    # PASSWORD = 'xoh12773' # demo 
   

    with create_ssl_socket(host, port) as sock:
        # Logowanie do API
        login_parameters = {
            "command": "login",
            "arguments": {
                "userId": USERID,
                "password": PASSWORD
            }
        }
        login_response = send_request(sock, login_parameters)
        if not login_response:
            logger.error('Logowanie nie powiodło się')
            return

        logger.info('Login response: ' + login_response)

        # Odpytanie o wszystkie symbole
        get_all_symbols_parameters = {"command": "getAllSymbols"}
        symbols_response = send_request(sock, get_all_symbols_parameters)
        if not symbols_response:
            logger.error('Brak odpowiedzi na zapytanie getAllSymbols.')
            return

        symbols_data = json.loads(symbols_response)
        if not symbols_data['status']:
            logger.error('Błąd w odpowiedzi: ' + str(symbols_data))
            return

        logger.info('Otrzymano dane symboli')
        
        # Tworzenie ramki danych z wyników
        all_symbols = pd.DataFrame(symbols_data['returnData'])
        if 'time' in all_symbols.columns:
            all_symbols['time'] = pd.to_datetime(all_symbols['time'], unit='ms', errors='coerce')

        logger.info(str(all_symbols))
        
        # Zapis danych do pliku CSV
        save_to_csv(all_symbols)

        # Wylogowanie
        logout_parameters = {"command": "logout"}
        logout_response = send_request(sock, logout_parameters)
        logger.info('Logout response: ' + logout_response)

if __name__ == '__main__':
    main()
