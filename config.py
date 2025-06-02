import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'some secret salt'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/SmartHome'
    SQLALCHEMY_TRACK_MODIFICATIONS = False