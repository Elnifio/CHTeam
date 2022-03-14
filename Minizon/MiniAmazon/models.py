from MiniAmazon import db


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)
    image = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # rating = db.relationship('Rating', lazy='dynamic')

    def __repr__(self):
        return f'<Item {self.name}>'


class Category(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)

    items = db.relationship('Item', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


cart = db.Table('cart',
                db.Column('item_id', db.Integer, db.ForeignKey('item.id'), primary_key=True),
                db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                db.Column('quantity', db.Integer, nullable=False)
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(100))
    password = db.Column(db.String(100))
    balance = db.Column(db.Integer, nullable=False, default=100)
    email = db.Column(db.Integer, nullable=False, unique=True)

    # add relationships below
    items_create = db.relationship('Item', backref='creator', lazy='dynamic')
    items_cart = db.relationship('Item', secondary='cart', lazy='select')

    def __repr__(self):
        return f'<User {self.name}>'

