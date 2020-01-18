from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_table import Table, Col
from views import views_api
from models import db, Usuario
from flask_login import LoginManager

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='')
app.config.from_pyfile('config.py')
db.init_app(app)
app.register_blueprint(views_api)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'views_api.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(user_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)