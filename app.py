import sys
import logging
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

# Настроим логирование для отладки и ошибок
logging.basicConfig(level=logging.INFO)

def main():
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        logging.info("Приложение запущено успешно.")
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {e}")
        sys.exit(1)  # Завершаем приложение с ошибкой

if __name__ == "__main__":
    main()
