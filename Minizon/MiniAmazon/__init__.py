from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

app = Flask(__name__)
# remove SQLALCHEMY_TRACK_MODIFICATIONS overhead warning
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# show sql expression
app.config['SQLALCHEMY_ECHO'] = True

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

db_name = 'postgres'
db_user = 'postgres'
db_password = 'password'
db_server = '34.207.91.24'
db_uri = f'postgresql://{db_user}:{db_password}@{db_server}/{db_name}'
db_uri_local = 'postgresql://postgres:@127.0.0.1/postgres'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@34.207.91.24/postgres'
# app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SECRET_KEY'] = '578e21533f06891a9260f6b4'
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri_local
app.config['UPLOAD_FOLDER'] = '/Users/shanqing/Desktop/CHTeam/Minizon/MiniAmazon/static/item_images'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'
login_manager.login_message_category='info'
# must run routes once
# from MiniAmazon import routes
