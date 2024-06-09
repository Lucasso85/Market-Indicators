import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

# Pliki do zapisywania stanu wybranych instrumentów i okresów
state_instruments_filename = 'selected_instruments.json'
state_periods_filename = 'selected_periods.json'
instruments_file = 'instruments.txt'

# Funkcja do wczytywania listy instrumentów z pliku
def load_instruments(file_path=instruments_file):
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
    with open(state_instruments_filename, 'w') as f:
        json.dump(selected_instruments, f)

# Funkcja do wczytywania stanu wybranych instrumentów
def load_selected_instruments():
    if os.path.exists(state_instruments_filename):
        with open(state_instruments_filename, 'r') as f:
            return json.load(f)
    return []

# Funkcja do zapisywania wybranych okresów
def save_selected_periods(selected_periods):
    with open(state_periods_filename, 'w') as f:
        json.dump(selected_periods, f)

# Funkcja do wczytywania wybranych okresów
def load_selected_periods():
    if os.path.exists(state_periods_filename):
        with open(state_periods_filename, 'r') as f:
            return json.load(f)
    return []

def main():
    """Główna funkcja skryptu wyboru instrumentów i okresów"""
    def on_start():
        """Obsługa przycisku start"""
        selected_instruments = [instr for instr, var in instruments_vars.items() if var.get()]
        selected_periods = [period for period, var in periods_vars.items() if var.get()]

        if not selected_instruments:
            messagebox.showwarning("Brak wyboru", "Proszę wybrać co najmniej jeden instrument.")
            return
        if not selected_periods:
            messagebox.showwarning("Brak wyboru", "Proszę wybrać co najmniej jeden okres.")
            return

        # Zapisanie wybranego stanu do plików
        save_selected_instruments(selected_instruments)
        save_selected_periods(selected_periods)
        messagebox.showinfo("Sukces", "Wybrane instrumenty i okresy zostały zapisane.")
        root.destroy()

    # Lista dostępnych instrumentów
    ALL_INSTRUMENTS = load_instruments()
    previous_selected_instruments = load_selected_instruments()
    previous_selected_periods = load_selected_periods()

    # Interfejs użytkownika
    root = tk.Tk()
    root.title("Wybór instrumentów i okresów")

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

    # Sekcja wyboru okresów
    periods_frame = ttk.Frame(root)
    periods_frame.pack(pady=10)
    ttk.Label(periods_frame, text="Wybierz okresy (minuty):").pack()

    available_periods = [5, 15, 60, 240, 1440]
    periods_vars = {}
    for period in available_periods:
        var = tk.BooleanVar(value=period in previous_selected_periods)
        chk = ttk.Checkbutton(periods_frame, text=f"{period} minut", variable=var)
        chk.pack(anchor='w')
        periods_vars[period] = var

    # Przycisk start
    btn_start = ttk.Button(root, text="Zapisz", command=on_start)
    btn_start.pack(pady=10)

    # Uruchomienie interfejsu użytkownika
    root.mainloop()

if __name__ == '__main__':
    main()
