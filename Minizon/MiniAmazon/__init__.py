from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# remove SQLALCHEMY_TRACK_MODIFICATIONS overhead warning
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db_name = 'postgres'
db_user = 'postgres'
db_password = 'password'
db_server = '34.207.91.24'
db_uri = f'postgresql://{db_user}:{db_password}@{db_server}/{db_name}'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@34.207.91.24/postgres'
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
db = SQLAlchemy(app)

# must run routes once
from MiniAmazon import routes
