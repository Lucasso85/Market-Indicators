import pandas as pd
import glob
import os
import logging
from datetime import datetime

# Konfiguracja loggera - ustawienia logowania
log_folder = 'logs'
os.makedirs(log_folder, exist_ok=True)
log_filename = os.path.join(log_folder, f'obliczenia_SMA_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Tworzenie loggera i ustawienie poziomu logowania
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# FileHandler - zapisywanie logów do pliku
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# StreamHandler - wyświetlanie logów w konsoli
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s %(levellevel)s %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Lista instrumentów i okresów
INSTRUMENTS = ['EURUSD', 'OIL.WTI', 'GOLD']  # Lista instrumentów
PERIODS = [5, 15, 60]  # Lista okresów w minutach
DATA_FOLDER = 'C:/Users/lukas/Desktop/Projekty PY/API dane gieldowe/LastRequest_data'  # Ścieżka do folderu z danymi
SYMBOLS_FOLDER = 'C:/Users/lukas/Desktop/Projekty PY/API dane gieldowe/ALL_Symbols_data'  # Ścieżka do folderu z plikami symbols
RESULTS_FOLDER = 'Results'  # Ścieżka do folderu z wynikami

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
    data = pd.read_csv(latest_file, usecols=['timestamp', 'open', 'close', 'INSTRUMENT'])
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    return data[['INSTRUMENT', 'timestamp', 'open', 'close']].sort_values(by='timestamp', ascending=False).head(200)

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

def main():
    """
    Główna funkcja programu: wczytywanie danych historycznych, tworzenie podsumowania, 
    wczytywanie najnowszego pliku symbols_*, dołączenie kolumny last_price i zapisanie summary_df do pliku CSV.
    """
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
    
    # Wybór kolumny "ask" z ALL_Symbols
    last_prices = ALL_Symbols[['symbol', 'ask']].rename(columns={'symbol': 'Instrument', 'ask': 'last_price'})
    
    # Dołączenie kolumny "last_price" do ramki danych summary_df
    summary_df = summary_df.merge(last_prices, on='Instrument', how='left')
    
    # Zapisanie summary_df do pliku CSV w folderze Results
    output_filename = os.path.join(RESULTS_FOLDER, "summary_data.csv")
    save_summary_to_csv(summary_df, output_filename)

    return summary_df

if __name__ == '__main__':
    summary_df = main()
    logger.info(summary_df)
