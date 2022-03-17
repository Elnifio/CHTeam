from MiniAmazon import db
from datetime import datetime

inventory = db.Table('inventory',
    db.Column('seller_id', db.Integer, db.ForeignKey('user.id'), nullable=False, primary_key=True),
    db.Column('item_id', db.Integer, db.ForeignKey('item.id'), nullable=False, primary_key=True),
    db.Column('quantity', db.Integer, nullable=False)
)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)
    image = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    rates = db.relationship("ItemRating", backref='item', lazy=True)

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
    password = db.Column(db.String(60), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=100)
    email = db.Column(db.String(100), nullable=False, unique=True)

    # add relationships below
    items_create = db.relationship('Item', backref='creator', lazy='dynamic')
    items_cart = db.relationship('Item', secondary='cart', lazy='select')

    receivers = db.relationship('Conversation', backref='sender',
                                lazy=True, foreign_keys="Conversation.sender_id")
    senders = db.relationship('Conversation', backref='receiver',
                              lazy=True, foreign_keys="Conversation.receiver_id")

    item_rates = db.relationship("ItemRating", backref='rater', lazy=True)
    item_votes = db.relationship("ItemUpvote", backref="voter", lazy=True)

    seller_rates = db.relationship("SellerRating", backref="seller",
                                   lazy=True, foreign_keys="SellerRating.rater_id")
    received_rates = db.relationship("SellerRating", backref="rater",
                                     lazy=True, foreign_keys="SellerRating.seller_id")
    seller_votes = db.relationship("SellerUpvote", backref="voter", lazy=True)

    seller_inventory = db.relationship('Item', secondary=inventory,
                                       lazy='dynamic', backref=db.backref('items', lazy=True))
    sell_order = db.relationship('Order', backref='sell_o', lazy=True, foreign_keys='Order.seller_id')

    def __repr__(self):
        return f'<User {self.id}>'


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(600), nullable=False, default="")
    ts = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return '<Conversation (%r -> %r) @ %r>: %r' % (self.sender, self.receiver, self.ts, self.content)


class ItemRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
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
    id = db.Column(db.Integer, primary_key=True)
    rating_id = db.Column(db.Integer, db.ForeignKey("item_rating.id"), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return "<Item Upvote> %r -> %r" % (self.rater, self.rating)


class SellerRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
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
    item_name = db.Column(db.String(length=30), nullable=False)
    address = db.Column(db.String(100))
    Date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    number_of_item = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Text, nullable=False)

    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_id = db.Column(db.Integer, nullable=False)

    items = db.relationship('Order', lazy='dynamic')

    def __repr__(self):
        return f'<Order {self.id}>'
   
