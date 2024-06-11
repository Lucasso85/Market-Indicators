import pandas as pd
import glob
import os
import logging
from datetime import datetime
import json
import numpy as np

# Konfiguracja loggera - ustawienia logowania
log_folder = 'logs'
os.makedirs(log_folder, exist_ok=True)
log_filename = os.path.join(log_folder, f'obliczenia_SMA_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Tworzenie loggera i ustawienie poziomu logowania
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Usunięcie wszystkich poprzednich handlerów, jeśli istnieją
if logger.hasHandlers():
    logger.handlers.clear()

# FileHandler - zapisywanie logów do pliku
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# StreamHandler - wyświetlanie logów w konsoli
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Stałe wartości
PERIODS = [ 15, 60, 240]  # Lista okresów w minutach
DATA_FOLDER = 'C:/Users/lukas/Desktop/Projekty PY/DASH_project/LastRequest_data'  # Ścieżka do folderu z danymi
SYMBOLS_FOLDER = 'C:/Users/lukas/Desktop/Projekty PY/DASH_project/ALL_Symbols_data'  # Ścieżka do folderu z plikami symbols
RESULTS_FOLDER = 'Results'  # Ścieżka do folderu z wynikami
INSTRUMENTS_FILE = 'selected_instruments.json'  # Ścieżka do pliku JSON z instrumentami

def load_instruments_from_json(file_path):
    """
    Wczytuje listę instrumentów z pliku JSON.
    """
    try:
        with open(file_path, 'r') as f:
            instruments = json.load(f)
        if not instruments:
            raise ValueError(f"Brak instrumentów w pliku {file_path}")
        return instruments
    except FileNotFoundError:
        logger.error(f"Plik {file_path} nie został znaleziony.")
        raise
    except json.JSONDecodeError:
        logger.error(f"Plik {file_path} nie jest poprawnym plikiem JSON.")
        raise

def load_latest_symbols_file(symbols_folder):
    """
    Wczytuje najnowszy plik symbols_* z podanego folderu.
    """
    pattern = os.path.join(symbols_folder, "symbols_*.csv")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No files matching pattern {pattern} found in {symbols_folder}")
    
    latest_file = files[0]
    logger.info(f"Wczytywanie danych z pliku: {latest_file}")
    return pd.read_csv(latest_file)

def load_data(symbol, period):
    """
    Wczytuje dane historyczne dla danego symbolu i okresu z najnowszego pliku CSV.
    """
    pattern = os.path.join(DATA_FOLDER, f"{symbol.lower()}_{period}min_*.csv")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No files matching pattern {pattern} found in {DATA_FOLDER}")
    
    latest_file = files[0]
    logger.info(f"Wczytywanie danych z pliku: {latest_file}")
    data = pd.read_csv(latest_file, usecols=['timestamp', 'open', 'close', 'high', 'low', 'INSTRUMENT'])
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    return data[['INSTRUMENT', 'timestamp', 'open', 'close' , 'high', 'low']].sort_values(by='timestamp', ascending=False).head(200)

def create_summary(all_data):
    """
    Tworzy podsumowanie danych z all_data, obliczając średnie z ostatnich 15, 50 i 200 wartości close.
    """
    summary_data = []

    for symbol, periods_data in all_data.items():
        for period, data in periods_data.items():
            latest_row = data.iloc[0]
            mean_15 = data['close'][:15].mean() if len(data) >= 15 else float('nan')
            mean_50 = data['close'][:50].mean() if len(data) >= 50 else float('nan')
            mean_200 = data['close'][:200].mean() if len(data) >= 200 else float('nan')

            summary_data.append({
                "Instrument": symbol,
                "Period": period,
                "timestamp": latest_row['timestamp'],
                "last_open": latest_row['open'],
                "last_close": latest_row['close'],
                'high': latest_row['high'],
                'low': latest_row['low'],
                "mean_15": mean_15,
                "mean_50": mean_50,
                "mean_200": mean_200
            })

    return pd.DataFrame(summary_data)
   

def save_summary_to_csv(summary_df, filename):
    """
    Zapisuje ramkę danych summary_df do pliku CSV o podanej nazwie.
    """
    summary_df.to_csv(filename, index=False)
    logger.info(f"Summary data saved to {filename}")
    
#### WSKAZNIKI oparte o srednie SMA ####
    
# wskaźnik HIT_15 - przałamanie sredniej 15-okresowej

def calculate_HIT_15(summary_df):
    # Konwersja kolumn na typ float, aby uniknąć problemów z typami danych
    summary_df['mean_15'] = summary_df['mean_15'].astype(float)
    summary_df['low'] = summary_df['low'].astype(float)
    summary_df['high'] = summary_df['high'].astype(float)
    
    # Warunek sprawdzający, czy srednia 15-okresowa zostala naruszona przez ostatnia swiece
    condition = (summary_df['mean_15'] >= summary_df['low']) & (summary_df['mean_15'] <= summary_df['high'])
    
    # Obliczanie wartości ilorazu MIN/'mean_15'
    min_diff = (pd.concat([(summary_df['mean_15'] - summary_df['low']).abs(),
                           (summary_df['mean_15'] - summary_df['high']).abs()], axis=1)).min(axis=1)
    ratio = min_diff / summary_df['last_close']
    
    # Ustawianie wartości wskaźnika HIT_15
    summary_df['HIT_15'] = np.where(condition, 1, np.round(ratio, 3))
    
    return summary_df

# wskaźnik HIT_50 - przałamanie sredniej 50-okresowej
def calculate_HIT_50(summary_df):
    # Konwersja kolumn na typ float, aby uniknąć problemów z typami danych
    summary_df['mean_50'] = summary_df['mean_50'].astype(float)
    summary_df['low'] = summary_df['low'].astype(float)
    summary_df['high'] = summary_df['high'].astype(float)
    
    # Warunek sprawdzający, czy srednia 50-okresowa zostala naruszona przez ostatnia swiece
    condition = (summary_df['mean_50'] >= summary_df['low']) & (summary_df['mean_50'] <= summary_df['high'])
    
    # Obliczanie wartości ilorazu MIN/'mean_15'
    min_diff = (pd.concat([(summary_df['mean_50'] - summary_df['low']).abs(),
                           (summary_df['mean_50'] - summary_df['high']).abs()], axis=1)).min(axis=1)
    ratio = min_diff / summary_df['last_close']
    
    # Ustawianie wartości wskaźnika HIT_50
    summary_df['HIT_50'] = np.where(condition, 1, np.round(ratio, 3))
    
    return summary_df

# wskaźnik HIT_200 - przałamanie sredniej 200-okresowej

def calculate_HIT_200(summary_df):
     summary_df['mean_200'] = summary_df['mean_200'].astype(float)
     summary_df['low'] = summary_df['low'].astype(float)
     summary_df['high'] = summary_df['high'].astype(float)
     
     # Warunek sprawdzajacy czy srednia 200-okresowa zostala naruszona przez ostatnia swiece
     condition = (summary_df['mean_200'] >= summary_df['low']) & (summary_df['mean_200'] <= summary_df['high'])

# Obliczanie wartości ilorazu MIN/'mean_200'
     min_diff = (pd.concat([(summary_df['mean_200'] - summary_df['low']).abs(),
                       (summary_df['mean_200'] - summary_df['high']).abs()], axis=1)).min(axis=1)
     ratio = min_diff / summary_df['last_close']

# Ustawianie wartości wskaźnika HIT_50
     summary_df['HIT_200'] = np.where(condition, 1, np.round(ratio, 3))

     return summary_df
    

def main():
    """
    Główna funkcja programu: wczytywanie danych historycznych, tworzenie podsumowania, 
    wczytywanie najnowszego pliku symbols_*, dołączenie kolumny last_price i zapisanie summary_df do pliku CSV.
    """
    # Wczytywanie instrumentów z pliku JSON
    try:
        INSTRUMENTS = load_instruments_from_json(INSTRUMENTS_FILE)
    except (FileNotFoundError, ValueError) as e:
        logger.error(e)
        return

    # Tworzenie folderu Results, jeśli nie istnieje
    if not os.path.exists(RESULTS_FOLDER):
        os.makedirs(RESULTS_FOLDER)

    all_data = {}
    for symbol in INSTRUMENTS:
        all_data[symbol] = {}
        for period in PERIODS:
            try:
                data = load_data(symbol, period)
                all_data[symbol][period] = data
                logger.info(f'Dane dla {symbol} (okres: {period} minut) wczytane pomyślnie.')
            except FileNotFoundError as e:
                logger.error(e)
    
    summary_df = create_summary(all_data)
    
    # Wczytanie najnowszego pliku symbols_* z folderu SYMBOLS_FOLDER
    ALL_Symbols = load_latest_symbols_file(SYMBOLS_FOLDER)
    
    # Wybór kolumny "bid" z ALL_Symbols
    last_prices = ALL_Symbols[['symbol', 'bid']].rename(columns={'symbol': 'Instrument', 'bid': 'last_price'})
    
    # Dołączenie kolumny "last_price" do ramki danych summary_df
    summary_df = summary_df.merge(last_prices, on='Instrument', how='left')
    
    # dolaczanie wskaznikow
    summary_df = calculate_HIT_15 (summary_df)
    summary_df = calculate_HIT_50 (summary_df)
   # summary_df = calculate_HIT_200 (summary_df)
    
    # Zapisanie summary_df do pliku CSV w folderze Results
    output_filename = os.path.join(RESULTS_FOLDER, "summary_data.csv")
    save_summary_to_csv(summary_df, output_filename)

    return summary_df

if __name__ == '__main__':
    summary_df = main()
    logger.info(summary_df)
