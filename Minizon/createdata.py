# ----------------
# REQUIRED MODULES
# ----------------
from MiniAmazon import db
from MiniAmazon.models import *
from sqlalchemy import func, case
from itertools import combinations
from datetime import datetime, timedelta
from sqlalchemy.orm import aliased

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
jump = False            # Controls if we skips the data generation part

# --------
# DATA GENERATION SPECIFIC CONFIG
# --------
CONVERSATION_P = 0.3

genconf = {
    'nusers': 15,               # Controls number of users generated
    "ncategories": 3,           # Controls number of categories generated
    'nitems': 30,               # Controls number of items generated
    "ninventoryrecords": 30,
    "norders": 30,
    'nitemratings': 20,         # Controls number of item ratings generated
    'nitemupvotes': 20,         # Controls number of item upvotes generated
    "nconversations": 20,       # Controls number of conversations generated
    "maxconversationlength": 20,# Controls maximum length of the conversation
    "nsellerratings": 20,
    "nsellerupvotes": 20,
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
        user = User(name="User %s" % i, password="TestPassword", email="user%s@email.com" % i)
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
def create_inventories():
    users = User.query.all()
    items = Item.query.all()

    for i in range(genconf['ninventoryrecords']):
        random.seed(new_seed())
        ioi = items[random.randint(0, len(items) - 1)]
        random.seed(new_seed())
        uoi = users[random.randint(0, len(users) - 1)]
        inv = Inventory(seller_id=uoi.id, item_id=ioi.id,
                        quantity=random.randint(0, 10),
                        price=random.uniform(2, 50))
        db.session.add(inv)
    db.session.commit()


@data_log()
def create_order():
    # Simulates the process of a user creating an order
    users = User.query.all()
    for i in range(genconf['norders']):
        random.seed(new_seed())
        uoi = users[random.randint(0, len(users)-1)]
        ooi = Order(address=uoi.address, buyer_id=uoi.id)
        items = Item.query.all()
        for item in items:
            chance = random.uniform(0, 1)
            if chance < 0.3:
                continue
            buyable = Inventory.query.filter(Inventory.item_id == item).all()
            if len(buyable) == 0:
                continue
            random.seed(new_seed())
            chosen = buyable[random.randint(0, len(buyable) - 1)]
            random.seed(new_seed())
            quantity = random.randint(1, chosen.quantity)
            oitem = Order_item(order_id=ooi.id, item_id=item.id, seller_id=chosen.seller_id,
                               quantity=quantity, price=chosen.price, fulfill="None")




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
        rating = ItemRating(rated_id=item.id, rater_id=commenter.id,
                            comment=comment, rate=random.randint(0, 5))
        db.session.add(rating)

    db.session.commit()


@data_log()
def create_item_upvotes():
    users = User.query.all()
    ratings = ItemRating.query.all()
    upvotes = []
    while len(upvotes) < genconf['nitemupvotes']:
        random.seed(new_seed())
        rating = ratings[random.randint(0, len(ratings) - 1)]
        random.seed(new_seed())
        voter = users[random.randint(0, len(users) - 1)]
        upvote = ItemUpvote(rating_id=rating.id, voter_id=voter.id)
        if (rating.id, voter.id) not in upvotes:
            upvotes.append((rating.id, voter.id))
            db.session.add(upvote)
        else:
            continue
    db.session.commit()


@data_log()
def create_seller_ratings():
    users = User.query.all()
    random.seed(new_seed())
    pairs = list(combinations(users, 2))
    random.shuffle(pairs)
    idx = 0

    for pair in pairs:
        if idx >= genconf['nsellerratings']:
            break

        random.seed(new_seed())
        commenter = pair[0]
        seller = pair[1]
        comment = f"User {commenter} commented to Seller {seller}"
        rating = SellerRating(rated_id=seller.id, rater_id=commenter.id,
                              comment=comment, rate=random.randint(0,5))

        idx += 1
        db.session.add(rating)

    db.session.commit()


@data_log()
def create_seller_upvotes():
    users = User.query.all()
    ratings = SellerRating.query.all()
    upvotes = []
    while len(upvotes) < genconf['nsellerupvotes']:
        random.seed(new_seed())
        rating = ratings[random.randint(0, len(ratings) - 1)]
        random.seed(new_seed())
        voter = users[random.randint(0, len(users) - 1)]
        upvote = SellerUpvote(rating_id=rating.id, voter_id=voter.id)
        if (rating.id, voter.id) not in upvotes:
            upvotes.append((rating.id, voter.id))
            db.session.add(upvote)
        else:
            continue
    db.session.commit()


@data_log()
def create_conversation():
    # Finds all users
    users = User.query.all()[::-1]
    pairs = combinations(users, 2)

    # Finds current time
    now = datetime.now()
    year = now.year
    month = now.month - 1

    # Creates pairs with number == genconf['nconversations']
    for pair in pairs:
        random.seed(new_seed())
        if random.uniform(0, 1) > CONVERSATION_P:
            continue

        # Generates the length of the conversation
        random.seed(new_seed())
        lenconversation = random.randint(1, genconf['maxconversationlength'])

        # Generates the base time to increment
        random.seed(new_seed())
        day = random.randint(1, 28)
        random.seed(new_seed())
        hour = random.randint(0, 23)
        random.seed(new_seed())
        minute = random.randint(0, 59)
        random.seed(new_seed())
        second = random.randint(0, 59)
        basetime = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)

        for _ in range(lenconversation):
            random.seed(new_seed())
            sender = random.randint(0, 1)
            receiver = (sender + 1) % 2
            sender = pair[sender]
            receiver = pair[receiver]
            msg = Conversation(
                sender_id=sender.id,
                receiver_id=receiver.id,
                content=f"Test Message from {sender.name} to {receiver.name}",
                ts=basetime
            )
            db.session.add(msg)

            random.seed(new_seed())
            second = random.randint(1, 24*60*60-1)
            random.seed(new_seed())
            day = random.randint(0,2)
            basetime = basetime + timedelta(days=day, seconds=second)

        db.session.commit()


# ----------------
# DATA GENERATION
# ----------------
@data_log()
def generate_data():
    # # Re-creates the table
    # drop_table()
    create_table()
    # # Create data entries
    # create_user()
    # create_categories()
    # create_items()
#     create_item_ratings()
#     create_item_upvotes()
    create_conversation()
#     create_seller_ratings()
#     create_seller_upvotes()
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
        result = ItemRating.query. \
            with_entities(func.avg(ItemRating.rate).label("average")). \
            filter(ItemRating.rated_id == item.id).all()
        print("Item %s rating: %s" % (item.id, round(result[0][0], 1) if result[0][0] is not None else result[0][0]))

    print("--------")
    query = ItemRating.query. \
        with_entities(func.count(ItemRating.rater_id).label("cnt"), ItemRating.rate). \
        group_by(ItemRating.rate)
    result = query.all()
    print("All items rate:", result)

    print("--------")
    for item in items:
        result = ItemRating.query.filter(ItemRating.rated_id == item.id). \
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
    # ----------------
    # Translates the following sql:
    # --------
    # select
    #     withname.id,
    #     withname.name,
    #     withname.item,
    #     withname.comment,
    #     withname.rate,
    #     withname.ts,
    #     count(upvote.voter_id),
    #     exists (
    #         select 1
    #     from upvote
    #         where
    #     withname.id == upvote.rating_id
    #     and
    #     upvote.voter_id == ?)
    # from upvote join (
    #         select
    #         rating.id as id,
    #         user.name as name,
    #         rating.rated_id as item,
    #         rating.comment as comment,
    #         rating.rate as rate,
    #         rating.ts as ts
    #     from rating join user on rating.rater_id == user.id
    #     where rating.rated_id == ?
    # ) as withname
    # on upvote.rating_id == withname.id
    # group by withname.id
    # --------
    # ?, ? represents (current user, current item)
    # ----------------

    subq = ItemRating.query.filter(ItemRating.rated_id == item.id). \
        join(User, User.id == ItemRating.rater_id). \
        outerjoin(ItemUpvote, ItemRating.id == ItemUpvote.rating_id). \
        group_by(ItemRating.id, User.name, ItemRating.rated_id, ItemRating.comment, ItemRating.rate, ItemRating.ts). \
        with_entities(
        ItemRating.id.label("rating_id"),
        User.name.label("name"),
        ItemRating.rated_id.label("rated_id"),
        ItemRating.comment.label("comment"),
        ItemRating.rate.label("rate"),
        ItemRating.ts.label("ts"),
        func.count(ItemUpvote.voter_id).label("num_upvotes"),
        func.max(
            case([(ItemUpvote.voter_id == user.id, 1)], else_=0)
        )
    )

    # q = subq.\
    #     join(ItemUpvote, subq.c.rating_id == ItemUpvote.rating_id). \
    #     group_by(subq.c.rating_id,
    #              subq.c.name,
    #              subq.c.rated_id,
    #              subq.c.comment,
    #              subq.c.rate,
    #              subq.c.ts).\
    #     with_entities(
    #         subq.c.rating_id.label("rating_id"),
    #         subq.c.name.label("commenter"),
    #         subq.c.rated_id.label("rated_id"),
    #         subq.c.comment.label("comment"),
    #         subq.c.rate.label("rate"),
    #         subq.c.ts.label("ts"),
    #         func.count(ItemUpvote.voter_id).label("num_upvotes"),
    #         func.max(
    #             case([(ItemUpvote.voter_id == user.id, 1)], else_=0)
    #         )
    #     )

    print("----------------")
    print(subq.all())
    print("----------------")


def conversations():
    uoi = User.query.filter(User.id == 17).all()[0]
    # q = Conversation.query.filter((Conversation.sender_id == uoi.id) | (Conversation.receiver_id == uoi.id))
    # q = q.order_by(Conversation.ts).with_entities(
    #     Conversation.sender.name.label("sender"),
    #     Conversation.receiver.name.label("receiver"),
    #     Conversation.content.label("content"),
    #     Conversation.ts.label("ts")
    # )

    senders = aliased(User)
    receivers = aliased(User)
    q = Conversation.query.filter((Conversation.sender_id == uoi.id) | (Conversation.receiver_id == uoi.id))
    q = q.join(senders, senders.id == Conversation.sender_id). \
        join(receivers, receivers.id == Conversation.receiver_id)
    q = q.with_entities(
        senders.name.label("Sender"),
        senders.id.label("Sender_id"),
        receivers.name.label("Receiver"),
        receivers.id.label("Receiver_id"),
        Conversation.content.label("Content"),
        Conversation.ts.label("Timestamp")
    ).order_by(Conversation.ts)

    print([x.Timestamp for x in q.all()])


# conversations()


def contacts():
    print("--------\n\n\n--------")
    uoi = User.query.filter(User.id == 17).all()[0]

    roi = Conversation.query.filter((Conversation.sender_id == uoi.id) | (Conversation.receiver_id == uoi.id))

    roi = roi.with_entities(
        case([(Conversation.sender_id == uoi.id, Conversation.receiver_id), ], else_=Conversation.sender_id).label("Other_id"),
        func.max(Conversation.ts).label("Ts"),
    ).group_by(case([(Conversation.sender_id == uoi.id, Conversation.receiver_id), ], else_=Conversation.sender_id))
    print("--------\n\nROI:\n\n--------")
    print(roi.all())

    roi = roi.subquery()

    senders = Conversation.query. \
        join(roi, (roi.c.Other_id == Conversation.sender_id) & (roi.c.Ts == Conversation.ts)). \
        filter(Conversation.receiver_id == uoi.id). \
        join(User, User.id == roi.c.Other_id). \
        with_entities(
        Conversation.ts.label("Timestamp"),
        Conversation.content.label("Content"),
        User.name.label("Other")
    )

    print("--------\n\nSenders:\n\n--------")
    print(senders.all())

    receivers = Conversation.query. \
        join(roi, (roi.c.Other_id == Conversation.receiver_id) & (roi.c.Ts == Conversation.ts)). \
        filter(Conversation.sender_id == uoi.id). \
        join(User, User.id == roi.c.Other_id). \
        with_entities(
        Conversation.ts.label("Timestamp"),
        Conversation.content.label("Content"),
        User.name.label("Other")
    )
    print("--------\n\nReceivers:\n\n--------")
    print(receivers.all())

    print("--------\n\n\n--------")
    for item in senders.union(receivers).all():
        print(f"Sent to {item.Other}: {item.Content} at {item.Timestamp}")

    print("--------\n\n\n--------")
    for item in map(
            lambda x: {"Other": x.Other, "Content": x.Content, "Timestamp": x.Timestamp},
            senders.union(receivers).order_by(Conversation.ts).all()):
        print(item)

    return


def find_rating_average_test():
    soi = 15
    coi = 6
    average = SellerRating.query.with_entities(func.avg(SellerRating.rate).label("average")). \
        filter(SellerRating.rated_id == soi).all()[0][0]

    q = SellerRating.query.filter(SellerRating.rated_id == soi). \
        join(User, User.id == SellerRating.rater_id). \
        outerjoin(SellerUpvote, SellerRating.id == SellerUpvote.rating_id). \
        group_by(SellerRating.id, User.name, SellerRating.rated_id, SellerRating.comment, SellerRating.rate, SellerRating.ts). \
        with_entities(
        SellerRating.id.label("rating_id"),
        User.name.label("name"),
        SellerRating.rated_id.label("rated_id"),
        SellerRating.comment.label("comment"),
        SellerRating.rate.label("rate"),
        SellerRating.ts.label("ts"),
        func.count(SellerUpvote.voter_id).label("num_upvotes"),
        func.max(
            case([(SellerUpvote.voter_id == coi, 1)], else_=0)
        ).label("is_voted")
    )

    distribution = SellerRating.query.filter(SellerRating.rated_id == soi). \
        with_entities(SellerRating.rate, func.count(SellerRating.rater_id).label("cnt")). \
        group_by(SellerRating.rate)

    current_review = SellerRating.query.filter(SellerRating.rated_id == soi, SellerRating.rater_id == coi)

    print("--------\n\n--------")
    # print(distribution.all())
    print(current_review.all())
    # ratings = q.all()
    # for item in ratings:
    #     print(item)
    #     print("----")




