import sys
import serial
import serial.tools.list_ports
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                           QLabel, QComboBox, QMessageBox, QHBoxLayout,
                           QGroupBox, QRadioButton, QLineEdit, QScrollArea)


class EncryptionEntry:
    def __init__(self, original, encrypted):
        self.original = original
        self.encrypted = encrypted


class DecryptionEntry:
    def __init__(self, original, decrypted):
        self.original = original
        self.decrypted = decrypted


class SelectableLabel(QLineEdit):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setReadOnly(True)
        self.setFrame(False) 
        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                padding: 5px;
            }
        """)

        self.setMinimumWidth(100)
        self.adjustSize()


class ResultBlock(QGroupBox):
    def __init__(self, original, encrypted, text, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        original_label = SelectableLabel(f"Original: {original}")
        layout.addWidget(original_label)

        encrypted_label = SelectableLabel(f"{text}: {encrypted}")
        layout.addWidget(encrypted_label)

        self.setLayout(layout)


class ArduinoInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('RSA encryption')
        self.setGeometry(100, 100, 1200, 800)

        self.history = []
        self.current_original = None

        self.layout = QHBoxLayout()

        left_container = QWidget()
        left_container.setFixedWidth(300)
        self.left_panel = QVBoxLayout()
        self.left_panel.setAlignment(Qt.AlignTop)

        connection_group = QGroupBox("Connection Settings")
        connection_layout = QVBoxLayout()

        port_row = QHBoxLayout()
        self.port_label = QLabel('Select Arduino Port:')
        self.port_selector = QComboBox()
        self.refresh_button = QPushButton('⟳')
        self.refresh_button.setToolTip('Refresh Ports')
        self.refresh_button.setFixedWidth(30)
        self.refresh_button.clicked.connect(self.refresh_ports)

        port_row.addWidget(self.port_label)
        port_row.addWidget(self.port_selector)
        port_row.addWidget(self.refresh_button)

        self.refresh_ports()
        self.connect_button = QPushButton('Connect')
        self.connect_button.clicked.connect(self.connect_arduino)

        connection_layout.addLayout(port_row)
        connection_layout.addWidget(self.connect_button)
        connection_group.setLayout(connection_layout)
        self.left_panel.addWidget(connection_group)

        key_group = QGroupBox("RSA Key Information")
        key_layout = QVBoxLayout()

        self.public_key_label = QLabel('Public Key: Not received')
        self.private_key_label = QLabel('Private Key: Not received')
        self.public_key_label.setWordWrap(True)
        self.private_key_label.setWordWrap(True)

        key_layout.addWidget(self.public_key_label)
        key_layout.addWidget(self.private_key_label)
        key_group.setLayout(key_layout)
        self.left_panel.addWidget(key_group)

        input_group = QGroupBox("Send Message")
        input_layout = QVBoxLayout()

        self.encrypt_message_input = QLineEdit()
        self.encrypt_message_input.returnPressed.connect(self.send_encrypt_message)
        self.encrypt_send_button = QPushButton('Encrypt')
        self.encrypt_send_button.clicked.connect(self.send_encrypt_message)
        self.encrypt_send_button.setEnabled(False)

        self.decrypt_message_input = QLineEdit()
        self.decrypt_message_input.returnPressed.connect(self.send_decrypt_message)
        self.decrypt_send_button = QPushButton('Decrypt')
        self.decrypt_send_button.clicked.connect(self.send_decrypt_message)
        self.decrypt_send_button.setEnabled(False)

        input_layout.addWidget(self.encrypt_message_input)
        input_layout.addWidget(self.encrypt_send_button)

        input_layout.addWidget(self.decrypt_message_input)
        input_layout.addWidget(self.decrypt_send_button)

        input_group.setLayout(input_layout)
        self.left_panel.addWidget(input_group)

        self.left_panel.addStretch()

        left_container.setLayout(self.left_panel)

        right_container = QWidget()
        right_layout = QVBoxLayout()

        format_group = QGroupBox("Output Format")
        format_layout = QHBoxLayout()

        self.format_decimal = QRadioButton("Decimal")
        self.format_hex = QRadioButton("Hexadecimal")
        self.format_binary = QRadioButton("Binary")
        self.format_decimal.setChecked(True)

        self.format_decimal.toggled.connect(self.update_encrypted_display)
        self.format_hex.toggled.connect(self.update_encrypted_display)
        self.format_binary.toggled.connect(self.update_encrypted_display)

        format_layout.addWidget(self.format_decimal)
        format_layout.addWidget(self.format_hex)
        format_layout.addWidget(self.format_binary)
        format_group.setLayout(format_layout)
        right_layout.addWidget(format_group)

        results_group = QGroupBox("Encryption Results")
        results_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.results_container = QWidget()
        self.results_container_layout = QVBoxLayout()
        self.results_container_layout.addStretch()
        self.results_container.setLayout(self.results_container_layout)

        scroll.setWidget(self.results_container)
        results_layout.addWidget(scroll)
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)

        right_container.setLayout(right_layout)

        self.layout.addWidget(left_container)
        self.layout.addWidget(right_container, 1)

        self.setLayout(self.layout)

        self.serial = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial)
        self.timer.start(100)

    def format_encrypted_data(self, data):
        try:
            numbers = [int(x) for x in data.split()]
            if self.format_hex.isChecked():
                return ' '.join([hex(x)[2:].upper().zfill(2) for x in numbers])
            elif self.format_binary.isChecked():
                return ' '.join([bin(x)[2:].zfill(8) for x in numbers])
            else: 
                return ' '.join([str(x) for x in numbers])
        except:
            return data

    def update_encrypted_display(self):
        while self.results_container_layout.count() > 1: 
            item = self.results_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for entry in reversed(self.history):
            block: ResultBlock
            if isinstance(entry, EncryptionEntry):
                block = ResultBlock(
                    entry.original,
                    self.format_encrypted_data(entry.encrypted),
                    "Encrypted",
                    self.results_container
                )
            else:
                block = ResultBlock(
                    entry.original,
                    entry.decrypted,
                    "Decrypted",
                    self.results_container
                )
            self.results_container_layout.insertWidget(0, block)

    def refresh_ports(self):
        current_port = self.port_selector.currentData()
        self.port_selector.clear()
        ports = serial.tools.list_ports.comports()

        for port in ports:
            try:
                ser = serial.Serial(port.device, 9600, timeout=1)
                ser.close()

                description = f"{port.device}"
                if port.description:
                    description += f" ({port.description})"
                if hasattr(port, 'serial_number') and port.serial_number:
                    description += f" - SN: {port.serial_number}"

                self.port_selector.addItem(description, port.device)

                if current_port and port.device == current_port:
                    index = self.port_selector.count() - 1
                    self.port_selector.setCurrentIndex(index)
            except (OSError, serial.SerialException):
                continue

    def connect_arduino(self):
        if self.serial is None or not self.serial.is_open:
            try:
                port = self.port_selector.currentData()
                if not port:
                    self.show_message("Error", "No port selected")
                    return

                self.serial = serial.Serial(port, 9600, timeout=1, rtscts=False, dsrdtr=False)
                self.serial.setDTR(False)

                self.connect_button.setText('Disconnect')
                self.encrypt_send_button.setEnabled(True)
                self.decrypt_send_button.setEnabled(True)
                self.port_selector.setEnabled(False)
                self.refresh_button.setEnabled(False)
                self.encrypt_message_input.setEnabled(True)
                self.show_message("Success", f"Connected to {port}")

            except Exception as e:
                self.show_message("Error", f"Failed to connect: {str(e)}")
                self.serial = None
        else:
            self.disconnect_arduino()

    def disconnect_arduino(self):
        if self.serial:
            port = self.serial.port
            self.serial.close()
            self.serial = None
            self.show_message("Disconnected", f"Disconnected from {port}")

        self.connect_button.setText('Connect')
        self.encrypt_send_button.setEnabled(False)
        self.encrypt_message_input.setEnabled(False)
        self.decrypt_send_button.setEnabled(False)
        self.decrypt_message_input.setEnabled(False)
        self.port_selector.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.refresh_ports()

    def send_encrypt_message(self):
        if not self.serial or not self.serial.is_open:
            self.show_message("Error", "Not connected to Arduino")
            return

        message = "e " + self.encrypt_message_input.text()
        if not message:
            return

        try:
            self.serial.write(message.encode())
            self.encrypt_message_input.clear()
        except Exception as e:
            self.show_message("Error", f"Failed to send message: {str(e)}")

    def send_decrypt_message(self):
        if not self.serial or not self.serial.is_open:
            self.show_message("Error", "Not connected to Arduino")
            return

        message = "d " + self.decrypt_message_input.text()
        if not message:
            return

        try:
            self.serial.write(message.encode())
            self.decrypt_message_input.clear()
        except Exception as e:
            self.show_message("Error", f"Failed to send message: {str(e)}")

    def read_serial(self):
        if self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    data = self.serial.readline().decode().strip()
                    if data:
                        print(data)
                        if "Public key:" in data:
                            self.public_key_label.setText(f"Public Key: {data.split('Public key:')[1].strip()}")
                        elif "Private key:" in data:
                            self.private_key_label.setText(f"Private Key: {data.split('Private key:')[1].strip()}")
                        else:
                            self.process_encryption_data(data)
            except:
                pass

    def process_encryption_data(self, data):
        if "Original:" in data:
            self.current_original = data.split('Original:')[1].strip()
        elif "Encrypted:" in data:
            encrypted_data = data.split('Encrypted:')[1].strip()
            if self.current_original:
                entry = EncryptionEntry(self.current_original, encrypted_data)
                self.history.append(entry)
                self.update_encrypted_display()
                self.current_original = None
        elif "Decrypted:" in data:
            decrypted_data = data.split('Decrypted:')[1].strip()
            if self.current_original:
                entry = DecryptionEntry(self.current_original, decrypted_data)
                self.history.append(entry)
                self.update_encrypted_display()
                self.current_original = None

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        self.disconnect_arduino()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ArduinoInterface()
    window.show()
    sys.exit(app.exec_())