import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QCheckBox, QRadioButton,
                             QPushButton, QGroupBox, QButtonGroup, QMessageBox)
from PyQt6.QtCore import Qt, QDateTime
import MySQLdb


class InsuranceCalculator(QMainWindow):
    def __init__(self):
        super().__init__()

        # Сначала инициализируем интерфейс
        self.init_ui()

        # Затем пробуем подключиться к БД
        self.db_connection = None
        self.cursor = None
        self.try_connect_db()

    def init_ui(self):
        self.setWindowTitle("Калькулятор страховых взносов")
        self.setFixedSize(794, 600)
        self.setStyleSheet("background-color: rgb(51, 51, 102);")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        layout = QVBoxLayout(central_widget)

        # Заголовок
        title = QLabel("Калькулятор страховых взносов и заработной платы")
        title.setStyleSheet("font: 25pt \"Akrobat\"; color: white; font-weight: bold; text-transform: uppercase;")
        layout.addWidget(title)

        # Выбор должности и отображение зарплаты
        position_layout = QHBoxLayout()
        position_label = QLabel("Должность")
        position_label.setStyleSheet("font: 14pt \"Akrobat\"; color: white; font-weight: bold;")

        self.position_combo = QComboBox()

        # Добавляем QLabel для отображения зарплаты
        self.salary_label = QLabel("Зарплата: ")
        self.salary_label.setStyleSheet("font: 14pt \"Akrobat\"; color: white; font-weight: bold;")

        position_layout.addWidget(position_label)
        position_layout.addWidget(self.position_combo)
        position_layout.addWidget(self.salary_label)
        position_layout.addStretch()

        layout.addLayout(position_layout)

        # Страховые взносы
        self.donations_group = QGroupBox("Выплачиваемые страховые взносы")
        self.donations_group.setStyleSheet("font: 14pt \"Akrobat\"; color: white; font-weight: bold;")
        self.donations_layout = QVBoxLayout()
        self.donations_group.setLayout(self.donations_layout)
        layout.addWidget(self.donations_group)

        # Тип операции
        self.operation_group = QGroupBox("Тип операции")
        self.operation_group.setStyleSheet("font: 14pt \"Akrobat\"; color: white; font-weight: bold;")
        operation_layout = QHBoxLayout()

        self.operation_buttons = QButtonGroup()
        self.salary_radio = QRadioButton("Заработная плата к выплате")
        self.donations_radio = QRadioButton("Сумма страховых взносов")
        self.salary_radio.setChecked(True)

        self.operation_buttons.addButton(self.salary_radio, 1)
        self.operation_buttons.addButton(self.donations_radio, 2)

        operation_layout.addWidget(self.salary_radio)
        operation_layout.addWidget(self.donations_radio)
        self.operation_group.setLayout(operation_layout)
        layout.addWidget(self.operation_group)

        # Кнопки
        buttons_layout = QHBoxLayout()
        self.calculate_btn = QPushButton("Рассчитать")
        self.save_btn = QPushButton("Записать")

        buttons_layout.addWidget(self.calculate_btn)
        buttons_layout.addWidget(self.save_btn)
        layout.addLayout(buttons_layout)

        # Результат
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font: 18pt \"Akrobat\"; color: white; font-weight: bold;")
        layout.addWidget(self.result_label)

        # Подключение сигналов
        self.calculate_btn.clicked.connect(self.calculate)
        self.save_btn.clicked.connect(self.save_operation)
        self.position_combo.currentIndexChanged.connect(self.update_salary_display)

    def try_connect_db(self):
        try:
            self.db_connection = MySQLdb.connect(
                host="localhost",
                user="root",
                passwd="root",
                db="pyqt_itogovaya_postovaya",
                charset='utf8mb4'
            )
            self.cursor = self.db_connection.cursor()
            self.load_data_from_db()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось подключиться: {str(e)}")
            self.save_btn.setEnabled(False)

    def load_data_from_db(self):
        try:
            # Загрузка должностей
            self.cursor.execute("SELECT id_position, p_name, p_salary FROM positions")
            self.positions_data = self.cursor.fetchall()

            self.position_combo.clear()
            for position in self.positions_data:
                self.position_combo.addItem(position[1], position[0])

            # Загрузка типов взносов
            self.load_donations_from_db()

            # Обновляем отображение зарплаты для первой должности
            if self.positions_data:
                self.update_salary_display()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", f"Ошибка при загрузке данных: {str(e)}")

    def update_salary_display(self):
        """Обновляет отображение зарплаты при изменении выбранной должности"""
        position_index = self.position_combo.currentIndex()
        if position_index >= 0 and self.positions_data:
            salary = self.positions_data[position_index][2]
            self.salary_label.setText(f"Зарплата: {salary:.2f} руб.")

    def load_donations_from_db(self):
        try:
            # Очищаем предыдущие чекбоксы
            for i in reversed(range(self.donations_layout.count())):
                widget = self.donations_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            self.donation_checkboxes = []

            # Загружаем данные из БД
            self.cursor.execute("SELECT id_donat, d_name, size FROM donations_type")
            self.donations_data = self.cursor.fetchall()

            # Добавляем новые чекбоксы (заблокированные и выбранные)
            for donation in self.donations_data:
                cb = QCheckBox(f"{donation[1]} ({donation[2]}%)")
                cb.setChecked(True)
                cb.setEnabled(False)  # Блокируем возможность изменения
                self.donation_checkboxes.append((donation[0], cb))
                self.donations_layout.addWidget(cb)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", f"Ошибка при загрузке взносов: {str(e)}")

    def calculate(self):
        try:
            position_index = self.position_combo.currentIndex()
            if position_index < 0:
                self.result_label.setText("Выберите должность!")
                return

            position_id = self.positions_data[position_index][0]
            position_name = self.positions_data[position_index][1]
            base_salary = float(self.positions_data[position_index][2])

            # Все взносы всегда выбраны (так как чекбоксы заблокированы)
            selected_donations = [str(donation[0]) for donation in self.donations_data]

            # Рассчитываем сумму всех взносов
            query = "SELECT SUM(size) FROM donations_type WHERE id_donat IN (%s)" % ",".join(
                ["%s"] * len(selected_donations))
            self.cursor.execute(query, selected_donations)
            result = self.cursor.fetchone()
            total_donations_percent = float(result[0]) if result[0] else 0
            total_donations = base_salary * total_donations_percent / 100

            operation_type = self.operation_buttons.checkedId()

            if operation_type == 1:
                result = base_salary - total_donations
                operation_name = "Заработная плата к выплате"
                self.result_label.setText(f"Зарплата к выплате: {result:.2f} руб.")
            else:
                result = total_donations
                operation_name = "Сумма страховых взносов"
                self.result_label.setText(f"Сумма страховых взносов: {result:.2f} руб.")

            # Сохраняем последний расчет
            self.last_calculation = {
                'position_id': position_id,
                'position_name': position_name,
                'operation_type': operation_type,
                'operation_name': operation_name,
                'amount': result,
                'base_salary': base_salary,
                'total_donations': total_donations
            }

        except Exception as e:
            self.result_label.setText(f"Ошибка: {str(e)}")

    def save_operation(self):
        if not hasattr(self, 'last_calculation'):
            QMessageBox.warning(self, "Ошибка", "Сначала выполните расчет!")
            return

        try:
            # Сохраняем запись в лог
            self.save_to_calc_log()

            # Вызываем хранимую процедуру
            self.call_stored_procedure()

            # Показываем последнюю операцию
            self.show_last_operation()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")

    def save_to_calc_log(self):
        if not hasattr(self, 'last_calculation') or not self.db_connection:
            return

        try:
            current_datetime = QDateTime.currentDateTime().toString(Qt.DateFormat.ISODate)
            log_message = (f"Расчет {self.last_calculation['operation_name']} для "
                           f"{self.last_calculation['position_name']}")

            query = """
                INSERT INTO calc_log (log_datetime, log_message, id_position, id_operation, calculated_amount)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                current_datetime,
                log_message,
                self.last_calculation['position_id'],
                self.last_calculation['operation_type'],
                self.last_calculation['amount']
            )

            self.cursor.execute(query, values)
            self.db_connection.commit()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить запись в лог: {str(e)}")
            if self.db_connection:
                self.db_connection.rollback()
            raise

    def call_stored_procedure(self):
        try:
            self.cursor.callproc('ProcessCalculation', (
                self.last_calculation['position_id'],
                self.last_calculation['operation_type']
            ))
            self.cursor.nextset()
            result = self.cursor.fetchone()
            if result:
                QMessageBox.information(self, "Результат", result[0])
            self.db_connection.commit()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при вызове процедуры: {str(e)}")
            if self.db_connection:
                self.db_connection.rollback()
            raise

    def show_last_operation(self):
        try:
            self.cursor.execute("""
                SELECT cl.log_datetime, p.p_name, ot.op_name, cl.calculated_amount, cl.log_message 
                FROM calc_log cl
                JOIN positions p ON cl.id_position = p.id_position
                JOIN operation_type ot ON cl.id_operation = ot.id_operation
                ORDER BY cl.log_datetime DESC
                LIMIT 1
            """)
            last_op = self.cursor.fetchone()

            if last_op:
                details = (
                    f"Последняя операция:\n\n"
                    f"Дата: {last_op[0]}\n"
                    f"Должность: {last_op[1]}\n"
                    f"Тип операции: {last_op[2]}\n"
                    f"Сумма: {last_op[3]:.2f} руб.\n\n"
                    f"{last_op[4]}"
                )
                QMessageBox.information(self, "История операций", details)

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить последнюю операцию: {str(e)}")

    def closeEvent(self, event):
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'db_connection') and self.db_connection:
                self.db_connection.close()
        except:
            pass
        event.accept()


if __name__ == "__main__":
    try:
        import MySQLdb
    except ImportError:
        print("Ошибка: Не установлена библиотека MySQLdb. Установите ее командой:")
        print("pip install mysqlclient")
        sys.exit(1)

    app = QApplication(sys.argv)

    try:
        window = InsuranceCalculator()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        sys.exit(1)