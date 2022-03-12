from MiniAmazon import app
from flask import render_template
from MiniAmazon.models import Item


@app.route('/')
@app.route('/home')
def home_page():
    print(111)
    return render_template('home.html')


@app.route('/market')
def market_page():
    items = Item.query.all()
    return render_template('market.html', items=items)
