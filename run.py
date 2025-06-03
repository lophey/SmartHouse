from app import create_app
from app.utils.serial_reader import start_serial_readers

# Створюємо додаток
app = create_app()

if __name__ == '__main__':
    # Запускаємо серійні читачі в окремому потоці
    start_serial_readers(app)
    # Запускаємо Flask додаток
    app.run(debug=True, use_reloader=False)