from app import create_app
from app.utils.serial_reader import start_serial_readers

app = create_app()

if __name__ == '__main__':

    start_serial_readers(app)

    app.run(debug=True, use_reloader=False)