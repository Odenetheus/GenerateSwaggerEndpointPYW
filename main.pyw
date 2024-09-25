# main.py

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QMessageBox, QAbstractItemView, QComboBox, QFileDialog
)
from PyQt5.QtCore import Qt
from core import fetch_spec, list_endpoints, generate_script, save_script

class SwaggerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Swagger API Script Generator')
        self.setGeometry(100, 100, 800, 600)
        self.spec = None
        self.endpoints = []
        self.selected_endpoints = []
        self.param_values = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # URL input
        self.url_label = QLabel('Enter Swagger/OpenAPI URL:')
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('e.g., https://example.com/swagger.yaml or https://example.com/swagger.json')
        self.fetch_button = QPushButton('Fetch API Specification')
        self.fetch_button.clicked.connect(self.on_fetch_spec)

        # Endpoints list
        self.endpoints_label = QLabel('Available Endpoints:')
        self.endpoints_list = QListWidget()
        self.endpoints_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.endpoints_list.itemSelectionChanged.connect(self.on_endpoint_selection_changed)

        # Language selection
        self.language_label = QLabel('Select Output Language:')
        self.language_combo = QComboBox()
        self.language_combo.addItems(['Python', 'C#', 'JavaScript', 'PHP'])

        # Separate files option
        self.separate_files_checkbox = QPushButton('Generate Separate Files for Each Endpoint')
        self.separate_files_checkbox.setCheckable(True)

        # Generate script button
        self.generate_button = QPushButton('Generate Script')
        self.generate_button.clicked.connect(self.on_generate_script)
        self.generate_button.setEnabled(False)

        # Add widgets to layout
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_input)
        layout.addWidget(self.fetch_button)
        layout.addWidget(self.endpoints_label)
        layout.addWidget(self.endpoints_list)
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)
        layout.addWidget(self.separate_files_checkbox)
        layout.addWidget(self.generate_button)

        self.setLayout(layout)

    def on_fetch_spec(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, 'Input Error', 'Please enter a valid URL.')
            return

        try:
            self.spec = fetch_spec(url)
            self.endpoints = list_endpoints(self.spec)
            self.populate_endpoints()
            self.generate_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to fetch specification:\n{e}')

    def populate_endpoints(self):
        self.endpoints_list.clear()
        for endpoint in self.endpoints:
            item_text = f"{endpoint['method']} {endpoint['path']} - {endpoint['summary']}"
            self.endpoints_list.addItem(item_text)

    def on_endpoint_selection_changed(self):
        selected_items = self.endpoints_list.selectedItems()
        if not selected_items:
            return

        self.selected_endpoints = []
        self.param_values = {}
        for item in selected_items:
            index = self.endpoints_list.row(item)
            endpoint = self.endpoints[index]
            self.selected_endpoints.append(endpoint)
            self.get_parameter_values(endpoint)

    def get_parameter_values(self, endpoint):
        params = endpoint.get('parameters', [])
        if not params:
            return

        param_values = {}
        for param in params:
            name = param['name']
            default = param.get('default', '')
            description = param.get('description', '')
            value, ok = QInputDialog.getText(self, 'Parameter Input',
                                             f"Enter value for parameter '{name}' ({param['in']}):\n{description}",
                                             QLineEdit.Normal, str(default))
            if ok:
                param_values[name] = value
            else:
                param_values[name] = ''
        self.param_values[endpoint['operationId']] = param_values

    def on_generate_script(self):
        if not self.selected_endpoints:
            QMessageBox.warning(self, 'Selection Error', 'Please select at least one endpoint.')
            return

        language = self.language_combo.currentText()
        separate_files = self.separate_files_checkbox.isChecked()
        output_dir = os.getcwd()

        if separate_files:
            output_dir = QFileDialog.getExistingDirectory(self, 'Select Output Directory')
            if not output_dir:
                QMessageBox.warning(self, 'Output Error', 'No output directory selected.')
                return

        for endpoint in self.selected_endpoints:
            operation_id = endpoint.get('operationId', 'endpoint')
            param_values = self.param_values.get(operation_id, {})
            try:
                code = generate_script(self.spec, endpoint, param_values, language)
                if separate_files:
                    filename = f"{operation_id}.{self.get_file_extension(language)}"
                    filepath = os.path.join(output_dir, filename)
                else:
                    filename = f"generated_script.{self.get_file_extension(language)}"
                    filepath = os.path.join(os.getcwd(), filename)
                save_script(code, filepath)
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to generate script for {operation_id}:\n{e}')
                return

        QMessageBox.information(self, 'Success', 'Scripts generated successfully.')

    def get_file_extension(self, language):
        extensions = {
            'Python': 'pyw',
            'C#': 'cs',
            'JavaScript': 'js',
            'PHP': 'php',
        }
        return extensions.get(language, 'txt')

if __name__ == '__main__':
    from PyQt5.QtWidgets import QInputDialog

    app = QApplication(sys.argv)
    window = SwaggerApp()
    window.show()
    sys.exit(app.exec_())
