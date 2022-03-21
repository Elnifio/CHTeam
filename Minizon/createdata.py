from MiniAmazon import db
from MiniAmazon.models import *
from sqlalchemy import func

jump = False
nusers = 5
ncategories = 3
nitems = 5
nitemratings = 15


if not jump:

    import random
    random.seed(42)
    print("Dropping all data")
    db.drop_all()
    print("Creating all data")
    db.create_all()

    users = []
    categories = []
    items = []

    print("    Creating Users")
    for i in range(nusers):
        user = User(name="User %s" % i, password="test password", email="user%s email" % i)
        users.append(user)
        db.session.add(user)

    db.session.commit()

    print("    Creating Categories")
    for i in range(ncategories):
        c = Category(name="Category %s" % i)
        categories.append(c)
        db.session.add(c)

    db.session.commit()

    random.shuffle(users)
    random.shuffle(categories)

    print("    Creating Items")
    for i in range(nitems):
        creator = users[i % len(users)]
        category = categories[i % len(categories)]
        item = Item(name="item %s" % i, description="description %s" % i,
                    category_id=category.id, creator_id=creator.id)

        items.append(item)
        db.session.add(item)

    db.session.commit()

    random.shuffle(items)

    print("    Create Ratings")
    for i in range(nitemratings):
        item = items[i % len(items)]
        commenter = users[i % len(users)]
        rating = ItemRating(item_id=item.id, rater_id=commenter.id,
                            comment="comment %s" % i, rate=random.randint(0, 5))
        db.session.add(rating)

    db.session.commit()

items = Item.query.all()

result = ItemRating.query.with_entities(func.avg(ItemRating.rate).label('average')).all()
print("All items average: %s" % round(result[0][0], 1) if result[0][0] is not None else result[0][0])
print("--------")

for item in items:
    result = ItemRating.query.with_entities(func.avg(ItemRating.rate).label("average")).filter(ItemRating.item_id == item.id).all()
    print("Item %s rating: %s" % (item.id, round(result[0][0], 1) if result[0][0] is not None else result[0][0]))

print("--------")
query = ItemRating.query.with_entities(func.count(ItemRating.rater_id).label("cnt"), ItemRating.rate).group_by(ItemRating.rate)
result = query.all()
print("All items rate:", result)

print("--------")
for item in items:
    result = ItemRating.query.filter(ItemRating.item_id == item.id).\
        with_entities(func.count(ItemRating.rater_id).label("cnt"), ItemRating.rate).\
        group_by(ItemRating.rate).all()
    print("Item", item.id, "rating:", result)


