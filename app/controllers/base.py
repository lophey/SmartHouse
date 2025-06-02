from flask import render_template, Blueprint

base_bp = Blueprint('base', __name__, url_prefix='/')

@base_bp.route('/')
def base():
    return render_template('base.html')