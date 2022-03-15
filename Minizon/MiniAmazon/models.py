from MiniAmazon import db
from datetime import datetime

inventory = db.Table('inventory',
    db.Column('seller_id', db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key = True),
    db.Column('item_id', db.Integer, db.ForeignKey('item.id'), nullable=False, primary_key = True),
    db.Column('quantity', db.Integer, nullable = False)
)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)
    image = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_item = db.relationship('Order', backref='items', lazy='dynamic')

    def __repr__(self):
        return f'<Item {self.name}>'


class Category(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)

    items = db.relationship('Item', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    item_create = db.relationship('Item', backref='creator', lazy='dynamic')
    seller_inventory = db.relationship('Item', secondary=inventory, lazy ='dynamic', backref=db.backref('items', lazy=True))
    sell_order = db.relationship('Order', backref='sell_o', lazy=True, foreign_keys='Order.seller_id')

    def __repr__(self):
        return f'<User {self.name}>'




class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(length=30), nullable=False)
    address = db.Column(db.String(100))
    Date = db.Column(db.DateTime, nullable=False, default = datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    number_of_item = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Text, nullable=False)

    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Order {self.name}>'
    
