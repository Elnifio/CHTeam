from MiniAmazon import db, login_manager, bcrypt
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select
# user log in doc: https://flask-login.readthedocs.io/en/latest/#how-it-works


class Inventory(db.Model):
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    seller = db.relationship('User', backref=db.backref('item_inventory', lazy='dynamic'))
    item = db.relationship('Item', backref=db.backref('user_inventory', lazy='dynamic'))


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)
    description = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    rates = db.relationship("ItemRating", backref='item', lazy='dynamic')
    images = db.relationship('ItemImage', lazy=True)

    @hybrid_property
    def price(self):
        total_price = self.user_inventory.with_entities(db.func.sum(Inventory.price)).first()[0]
        return round(total_price/self.user_inventory.count(), 2)

    @price.expression
    def price(cls):
        return(
            select([db.func.avg(Inventory.price)]).
            where(cls.id == Inventory.item_id).
            label('price')
        )

    @hybrid_property
    def rating(self):
        count = self.rates.count()
        total_rating = self.rates.with_entities(db.func.sum(ItemRating.rate)).first()[0]
        # print(self.id, " ", total_rating)
        return round(total_rating/self.rates.count(), 1) if count > 0 else 0.0

    @rating.expression
    def rating(cls):
        return(
            select([db.func.coalesce(db.func.avg(ItemRating.rate), 0)]).
            where(cls.id == ItemRating.rated_id).
            label('rating')
        )

    def __repr__(self):
        return f'<Item {self.name}>'


class ItemImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=True)

    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))

    def __repr__(self):
        return f'<Item {self.name}>'


class Category(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)

    items = db.relationship('Item', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Cart(db.Model):
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    buyer = db.relationship('User', backref=db.backref('item_cart', lazy='dynamic'), foreign_keys=[buyer_id])
    item = db.relationship('Item')
    seller = db.relationship('User', foreign_keys=[seller_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(100))
    password = db.Column(db.String(60), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=100)
    email = db.Column(db.String(100), nullable=False, unique=True)

    # add relationships below
    items_create = db.relationship('Item', backref='creator', lazy='dynamic')

    receivers = db.relationship('Conversation', backref='sender',
                                lazy=True, foreign_keys="Conversation.sender_id")
    senders = db.relationship('Conversation', backref='receiver',
                              lazy=True, foreign_keys="Conversation.receiver_id")

    item_rates = db.relationship("ItemRating", backref='rater', lazy=True)
    item_votes = db.relationship("ItemUpvote", backref="voter", lazy=True)

    seller_rates = db.relationship("SellerRating", backref="seller",
                                   lazy='dynamic', foreign_keys="SellerRating.rater_id")
    received_rates = db.relationship("SellerRating", backref="rater",
                                     lazy='dynamic', foreign_keys="SellerRating.rated_id")
    seller_votes = db.relationship("SellerUpvote", backref="voter", lazy=True)

    seller_inventory = db.relationship('Item', secondary='inventory',
                                       lazy='dynamic', backref=db.backref('sellers', lazy='dynamic'), viewonly=True)

    @property
    def password_plain(self):
        return self.password_plain

    @password_plain.setter
    def password_plain(self, plaintext):
        self.password = bcrypt.generate_password_hash(plaintext).decode('utf-8')

    @hybrid_property
    def rating(self):
        # print(self.received_rates.count())
        avg = self.received_rates.with_entities(db.func.avg(SellerRating.rate)).first()[0]
        return 0.0 if avg is None else round(avg, 1)

    @rating.expression
    def rating(cls):
        return(
            select([db.func.coalesce(db.func.avg(SellerRating.rate), 0)]).
            where(cls.id == SellerRating.seller_id).
            label('rating')
        )

    def check_password_correct(self, plaintext):
        return bcrypt.check_password_hash(self.password, plaintext)

    def __repr__(self):
        return f'<User {self.id}>'


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(600), nullable=False, default="")
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    priority = db.Column(db.Integer, nullable=False, default=0)
    
    def __repr__(self):
        return '<Conversation (%r -> %r) @ %r>: %r' % (self.sender, self.receiver, self.ts, self.content)


class ItemRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rated_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    rater_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.String(1000), nullable=False, default="")
    rate = db.Column(db.Integer, nullable=False, default=5)
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    upvotes = db.relationship("ItemUpvote", backref="rating", lazy=True)

    rateNonNegative = db.CheckConstraint("rate >= 0", name="rateNonNegative")
    rateMaximum = db.CheckConstraint("rate <= 5", name="rateMaximum")

    def __repr__(self):
        return "<%r Item Rating: (%r -> %r) @ %r>: %r" % (self.rate, self.rater, self.item, self.ts, self.comment)


class ItemUpvote(db.Model):
    rating_id = db.Column(db.Integer, db.ForeignKey("item_rating.id"), nullable=False, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True)

    def __repr__(self):
        return "<Item Upvote> %r -> %r" % (self.voter, self.rating)


class SellerRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rated_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rater_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.String(1000), nullable=False, default="")
    rate = db.Column(db.Integer, nullable=False, default=5)
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    upvotes = db.relationship("SellerUpvote", backref="rating", lazy=True)

    rateNonNegative = db.CheckConstraint("rate >= 0", name="rateNonNegative")
    rateMaximum = db.CheckConstraint("rate <= 5", name="rateMaximum")

    def __repr__(self):
        return "<%r Seller Rating: (%r -> %r) @ %r>: %r" % (self.rate, self.rater, self.seller, self.ts, self.comment)


class SellerUpvote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating_id = db.Column(db.Integer, db.ForeignKey("seller_rating.id"), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return "<Seller Upvote> %r -> %r" % (self.rater, self.rating)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(100))
    Date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.Text, nullable=False)

    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    buyer = db.relationship('User', backref=db.backref('buyer_order', lazy='dynamic'))

    def __repr__(self):
        return f'<Order {self.id}>'


class Order_item(db.Model):
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True) 
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    fulfill = db.Column(db.String, nullable=False)

    seller = db.relationship('User', backref='sell_order')
    order = db.relationship('Order', backref='order_items')
    item = db.relationship('Item', backref='order_item')


