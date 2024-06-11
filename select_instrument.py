from PyQt5 import QtWidgets, QtCore
import sys
import csv
import json
import os

state_instruments_filename = 'selected_instruments.json'
state_periods_filename = 'selected_periods.json'
instruments_file = 'instruments.csv'

def load_instruments(file_path=instruments_file):
    instruments = {}
    with open(file_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            group = row['categoryName']
            subgroup = row['groupName']
            instrument = row['symbol']
            description = row['description']
            type_subgroup = row['type']

            if group not in instruments:
                instruments[group] = {}
            
            if group == 'STC':
                if subgroup not in instruments[group]:
                    instruments[group][subgroup] = {}
                if type_subgroup not in instruments[group][subgroup]:
                    instruments[group][subgroup][type_subgroup] = []
                instruments[group][subgroup][type_subgroup].append((instrument, description))
            else:
                if subgroup not in instruments[group]:
                    instruments[group][subgroup] = []
                instruments[group][subgroup].append((instrument, description))

    return instruments

def save_selected_instruments(selected_instruments):
    with open(state_instruments_filename, 'w') as f:
        json.dump(selected_instruments, f)

def load_selected_instruments():
    if os.path.exists(state_instruments_filename):
        with open(state_instruments_filename, 'r') as f:
            return json.load(f)
    return []

def save_selected_periods(selected_periods):
    with open(state_periods_filename, 'w') as f:
        json.dump(selected_periods, f)

def load_selected_periods():
    if os.path.exists(state_periods_filename):
        with open(state_periods_filename, 'r') as f:
            return json.load(f)
    return []

class CheckableTree(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super(CheckableTree, self).__init__(parent)
        self.setHeaderLabels(['Instruments'])
        self.itemChanged.connect(self.handle_item_changed)

    def handle_item_changed(self, item, column):
        if item.checkState(column) == QtCore.Qt.Checked:
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, QtCore.Qt.Checked)
        elif item.checkState(column) == QtCore.Qt.Unchecked:
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, QtCore.Qt.Unchecked)

    def add_items(self, instruments, previous_selected_instruments):
        for group, subgroups in instruments.items():
            group_item = QtWidgets.QTreeWidgetItem(self)
            group_item.setText(0, group)
            group_item.setFlags(group_item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
            for subgroup, subgroups2 in subgroups.items():
                subgroup_item = QtWidgets.QTreeWidgetItem(group_item)
                subgroup_item.setText(0, subgroup)
                subgroup_item.setFlags(subgroup_item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)

                if group == 'STC':  # dla grupy STC
                    for type_subgroup, instr in subgroups2.items():
                        type_item = QtWidgets.QTreeWidgetItem(subgroup_item)
                        type_item.setText(0, type_subgroup)
                        type_item.setFlags(type_item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
                        for symbol, description in instr:
                            item = QtWidgets.QTreeWidgetItem(type_item)
                            item.setText(0, f"{symbol} - {description}")
                            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                            item.setCheckState(0, QtCore.Qt.Checked if symbol in previous_selected_instruments else QtCore.Qt.Unchecked)
                else:  # dla innych grup
                    for symbol, description in subgroups2:
                        item = QtWidgets.QTreeWidgetItem(subgroup_item)
                        item.setText(0, f"{symbol} - {description}")
                        item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                        item.setCheckState(0, QtCore.Qt.Checked if symbol in previous_selected_instruments else QtCore.Qt.Unchecked)

    def get_selected_symbols(self):
        selected_symbols = []
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                subgroup_item = group_item.child(j)
                if group_item.text(0) == 'STC':  # dla grupy STC
                    for k in range(subgroup_item.childCount()):
                        type_item = subgroup_item.child(k)
                        for l in range(type_item.childCount()):
                            item = type_item.child(l)
                            if item.checkState(0) == QtCore.Qt.Checked:
                                selected_symbols.append(item.text(0).split(' - ')[0])
                else:  # dla innych grup
                    for k in range(subgroup_item.childCount()):
                        item = subgroup_item.child(k)
                        if item.checkState(0) == QtCore.Qt.Checked:
                            selected_symbols.append(item.text(0).split(' - ')[0])
        return selected_symbols

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Wybór instrumentów i okresów')
        self.layout = QtWidgets.QVBoxLayout(self)

        self.tree = CheckableTree()
        self.layout.addWidget(self.tree)

        periods_frame = QtWidgets.QFrame()
        periods_layout = QtWidgets.QVBoxLayout(periods_frame)
        periods_layout.addWidget(QtWidgets.QLabel("Wybierz okresy (minuty):"))

        self.periods_vars = {}
        available_periods = [5, 15, 60, 240, 1440]
        previous_selected_periods = load_selected_periods()
        for period in available_periods:
            chk = QtWidgets.QCheckBox(f"{period} minut")
            chk.setChecked(period in previous_selected_periods)
            periods_layout.addWidget(chk)
            self.periods_vars[period] = chk
        self.layout.addWidget(periods_frame)

        self.save_button = QtWidgets.QPushButton("Zapisz")
        self.save_button.clicked.connect(self.save_selection)
        self.layout.addWidget(self.save_button)

        instruments = load_instruments()
        previous_selected_instruments = load_selected_instruments()
        self.tree.add_items(instruments, previous_selected_instruments)

    def save_selection(self):
        selected_instruments = self.tree.get_selected_symbols()
        selected_periods = [period for period, chk in self.periods_vars.items() if chk.isChecked()]

        if not selected_instruments:
            QtWidgets.QMessageBox.warning(self, "Brak wyboru", "Proszę wybrać co najmniej jeden instrument.")
            return
        if not selected_periods:
            QtWidgets.QMessageBox.warning(self, "Brak wyboru", "Proszę wybrać co najmniej jeden okres.")
            return

        save_selected_instruments(selected_instruments)
        save_selected_periods(selected_periods)
        QtWidgets.QMessageBox.information(self, "Sukces", "Wybrane instrumenty i okresy zostały zapisane.")
        self.close()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
