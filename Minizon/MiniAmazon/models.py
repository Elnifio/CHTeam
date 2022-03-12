from MiniAmazon import db


class Item(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(length=30), nullable=False)
    image = db.Column(db.String(100))
    category = db.Column(db.String(100))
    rating = db.Column(db.Numeric())
    price = db.Column(db.Numeric(), nullable=False)
    description = db.Column(db.String(200), nullable=False)
