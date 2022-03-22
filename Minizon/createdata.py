# ----------------
# REQUIRED MODULES
# ----------------
from MiniAmazon import db
from MiniAmazon.models import *
from sqlalchemy import func

# ----------------
# RANDOM GENERATOR
# ----------------
import random
rconfig = {
    "nseeds": 100,
    "seeds": [],
    "chosen_seed": 0
}
random.seed(42)
rconfig['seeds'] = list(range(rconfig['nseeds']))
random.shuffle(rconfig['seeds'])


def new_seed():
    rconfig['chosen_seed'] += 1
    return rconfig['seeds'][rconfig['chosen_seed'] % len(rconfig['seeds'])]


# ----------------
# CONFIGS
# ----------------
jump = True            # Controls if we skips the data generation part

# --------
# DATA GENERATION SPECIFIC CONFIG
# --------
genconf = {
    'nusers': 15,               # Controls number of users generated
    "ncategories": 3,           # Controls number of categories generated
    'nitems': 30,               # Controls number of items generated
    'nitemratings': 20,         # Controls number of item ratings generated
    'nitemupvotes': 20,         # Controls number of item upvotes generated
    'indent': -1
}


# ----------------
# Data Creation Functions
# ----------------
# decorator for logging function calls
def data_log(start="", end=""):
    def decorator(func):
        def wrapper(*args, **kw):
            genconf['indent'] += 1
            print(''.join([' |  ' for _ in range(genconf['indent'])]) + "Calling " + " ".join(func.__name__.split("_")))
            result = func(*args, **kw)
            print(''.join([' |  ' for _ in range(genconf['indent'])]) + "Exited " + " ".join(func.__name__.split("_")))
            genconf['indent'] -= 1
            return result
        return wrapper
    return decorator


# Helper method for formatting printed outputs within each function calls
def data_print(content):
    genconf['indent'] += 1
    print(''.join([' |  ' for _ in range(genconf['indent'])]) + content)
    genconf['indent'] -= 1


@data_log()
def drop_table():
    db.drop_all()


@data_log()
def create_table():
    db.create_all()


@data_log()
def create_user():
    for i in range(genconf['nusers']):
        user = User(name="User %s" % i, password="test password", email="user%s email" % i)
        db.session.add(user)
    db.session.commit()


@data_log()
def create_categories():
    for i in range(genconf['ncategories']):
        c = Category(name="Category %s" % i)
        db.session.add(c)
    db.session.commit()


@data_log()
def create_items():
    users = User.query.all()
    categories = Category.query.all()
    for i in range(genconf['nitems']):
        random.seed(new_seed())
        creator = users[random.randint(0, len(users) - 1)]
        random.seed(new_seed())
        category = categories[random.randint(0, len(categories) - 1)]
        item = Item(name="item %s" % i, description="description %s" % i,
                    category_id=category.id, creator_id=creator.id)
        db.session.add(item)
    db.session.commit()


@data_log()
def create_item_ratings():
    users = User.query.all()
    items = Item.query.all()
    for i in range(genconf['nitemratings']):
        random.seed(new_seed())
        item = items[random.randint(0, len(items) - 1)]
        random.seed(new_seed())
        commenter = users[random.randint(0, len(users) - 1)]
        comment = "Comment %s: User %r commented on item %r" % (i, commenter, item)
        rating = ItemRating(item_id=item.id, rater_id=commenter.id,
                            comment=comment, rate=random.randint(0, 5))
        db.session.add(rating)

    db.session.commit()


@data_log()
def create_item_upvotes():
    users = User.query.all()
    ratings = ItemRating.query.all()
    for _ in range(genconf['nitemupvotes']):
        random.seed(new_seed())
        rating = ratings[random.randint(0, len(ratings) - 1)]
        random.seed(new_seed())
        voter = users[random.randint(0, len(users) - 1)]
        upvote = ItemUpvote(rating_id=rating.id, voter_id=voter.id)
        db.session.add(upvote)
    db.session.commit()


# ----------------
# DATA GENERATION
# ----------------
@data_log()
def generate_data():
    # Re-creates the table
    drop_table()
    create_table()
    # Create data entries
    create_user()
    create_categories()
    create_items()
    create_item_ratings()
    create_item_upvotes()
    return


if not jump:
    generate_data()


# ----------------
# Data Query Experimentation
# ----------------
def item_rating_average_test():
    items = Item.query.all()

    result = ItemRating.query.with_entities(func.avg(ItemRating.rate).label('average')).all()
    print("All items average: %s" % round(result[0][0], 1) if result[0][0] is not None else result[0][0])
    print("--------")

    for item in items:
        result = ItemRating.query.\
            with_entities(func.avg(ItemRating.rate).label("average")).\
            filter(ItemRating.item_id == item.id).all()
        print("Item %s rating: %s" % (item.id, round(result[0][0], 1) if result[0][0] is not None else result[0][0]))

    print("--------")
    query = ItemRating.query.\
        with_entities(func.count(ItemRating.rater_id).label("cnt"), ItemRating.rate).\
        group_by(ItemRating.rate)
    result = query.all()
    print("All items rate:", result)

    print("--------")
    for item in items:
        result = ItemRating.query.filter(ItemRating.item_id == item.id). \
            with_entities(func.count(ItemRating.rater_id).label("cnt"), ItemRating.rate). \
            group_by(ItemRating.rate).all()
        print("Item", item.id, "rating:", result)

# item_rating_average_test()

def item_upvote_test():
    users = User.query.all()
    users = sorted(users, key=lambda x: len(x.item_votes), reverse=True)
    ratings = ItemRating.query.all()
    designated = users[:3]

    for user in designated:
        print("Querying for user " + user.__repr__())
        for rating in ratings:
            queried = ItemUpvote.query.filter(rating.id == ItemUpvote.rating_id, user.id == ItemUpvote.voter_id).all()
            print("    Voting record for rating '" + rating.comment + "': " + str(queried))

# item_upvote_test()

def item_upvote_test2():
    user = User.query.filter(User.id == 1).all()[0]
    item = Item.query.filter(Item.id == 22).all()[0]
    query = ItemRating.query.filter(ItemRating.item_id == item.id)
    query = query.with_entities(
        ItemRating.rater.label("commenter"),
        ItemRating.comment.label("comment"),
        ItemRating.rate.label("rate"),
        ItemRating.ts.label("timestamp"),
        func.count(ItemRating.upvotes).label("all_counts"),
        ItemRating.upvotes.any(voter_id=user.id).label("is_voted")
    )
    query = query.group_by(ItemRating.rater)
    print(query.all())

item_upvote_test2()



