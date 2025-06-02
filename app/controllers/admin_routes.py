from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.forms import AdminLoginForm
from app.models.user import User
from app.models.room import Room
from app.models.device import Device
from app.utils.serial_reader import start_serial_readers

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = AdminLoginForm()  # Створення форми

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data) and user.is_admin():
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('admin.dashboard'))

        flash('Невірні облікові дані або недостатньо прав', 'danger')

    return render_template('admin/admin_login.html', form=form)  # Передаємо форму у шаблон

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin():
        flash('Доступ заборонено', 'danger')
        return redirect(url_for('user.dashboard'))
    return render_template('admin/admin_main.html')

@admin_bp.route('/rooms')
@login_required
def manage_rooms():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))

    rooms = Room.query.all()
    return render_template('admin/admin_main.html', rooms=rooms)

@admin_bp.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        port = request.form['port']

        new_room = Room(
            name=name,
            description=description,
            controller_port=port
        )
        db.session.add(new_room)
        db.session.commit()

        # Перезапуск слушателей портов
        start_serial_readers(current_app._get_current_object())

        flash('Room added successfully', 'success')
        return redirect(url_for('admin.manage_rooms'))

    return render_template('admin/add_room.html')

@admin_bp.route('/delete_room/<int:room_id>', methods=['POST'])
@login_required
def delete_room(room_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('user.dashboard'))

    room = Room.query.get(room_id)
    if room:
        db.session.delete(room)
        db.session.commit()
        flash('Room deleted successfully', 'success')
    else:
        flash('Room not found', 'danger')

    return redirect(url_for('admin.manage_rooms'))

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))