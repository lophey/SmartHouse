from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegistrationForm(FlaskForm):
    username = StringField('Логін', validators=[
        DataRequired(),
        Length(min=4, max=20, message="Логін повинен бути від 4 до 20 символів")
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message="Невірний формат email")
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=8, message="Пароль повинен містити принаймні 8 символів")
    ])
    confirm_password = PasswordField('Підтвердження паролю', validators=[
        DataRequired(),
        EqualTo('password', message="Паролі не співпадають")
    ])
    accept_tos = BooleanField('Я погоджуюсь з умовами використання', validators=[DataRequired()])
    submit = SubmitField('Зареєструватись')

class LoginForm(FlaskForm):
    username = StringField('Логін', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запам\'ятати мене')
    submit = SubmitField('Увійти')

class AdminLoginForm(FlaskForm):
    username = StringField('Адміністративний логін', validators=[DataRequired()])
    password = PasswordField('Адміністративний пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запам\'ятати мене')
    submit = SubmitField('Увійти як адміністратор')