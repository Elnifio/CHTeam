from MiniAmazon import db
from MiniAmazon.models import *
from sqlalchemy import func

import random
random.seed(42)

db.drop_all()
db.create_all()

users = []
categories = []
items = []

for i in range(5):
    user = User(name="User %s" % i, password="test password", email="user%s email" % i)
    users.append(user)
    db.session.add(user)

db.session.commit()

for i in range(3):
    c = Category(name="Category %s" % i)
    categories.append(c)
    db.session.add(c)

db.session.commit()

random.shuffle(users)
random.shuffle(categories)

for i in range(5):
    creator = users[i % len(users)]
    category = categories[i % len(categories)]
    item = Item(name="item %s" % i, price=random.randint(1, 20),
                description="description %s" % i, category_id=category.id,
                creator_id=creator.id)

    items.append(item)
    db.session.add(item)

db.session.commit()

random.shuffle(items)

for i in range(5):
    item = items[i % len(items)]
    commenter = users[i % len(users)]
    rating = ItemRating(item_id=item.id, rater_id=commenter.id,
                        comment="comment %s" % i, rate=random.randint(0, 5))
    db.session.add(rating)

db.session.commit()

result = ItemRating.query.with_entities(func.avg(ItemRating.rate).label('average')).all()

print(result)
