from flask import Blueprint, render_template
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('home.html', year=datetime.now().year)

@main_bp.route('/test-template')
def test_template():
    return render_template('login.html') 