from MiniAmazon import db
from MiniAmazon.models import Category, Item, User, Inventory
import random

amazon_categories = \
["Appliances", "Apps & Games", "Arts, Crafts & Sewing", "Audible Books & Originals", \
 "Automotive Parts & Accessories", "Baby", "Beauty & Personal Care", "Books", "CDs & Vinyl", \
 "Cell Phones & Accessories", "Clothing, Shoes & Jewelry", "Collectibles & Fine Art", "Computers",
 "Credit and Payment Carts", "Digital Educational Resources", "Digital Music", "Electronics", \
 "Garden & Outdoor", "Gift Cards", "Grocery & Gourmet Food", "Handmade", "Health, Household & Baby Care", \
 "Home & Kitchen", "Industrial & Scientific", "Luggage & Travel Gear", "Luxury Stores", \
 "Magazines", "Movies & TV", "Musical Instruments", "Office Products", "Pet Supplies", "Smart Home", \
 "Software", "Sports & Outdoors", "Tools & Home Improvement", "Toys & Games", "Video Games"]

print("******** category import start ********")

for c in amazon_categories:
    print(f"importing category: {c}")
    db.session.add(Category(name=c))

db.session.commit()
print("******** category import end ********")


descriptions = []
with open('descriptions.txt') as f:
    word = f.readline()
    while word:
        descriptions.append(word[:-1])
        word = f.readline()
    f.close()

print("************ item import start *************")

price_range = [0, 100, 200, 300, 400, 500, 600, 700, 900, 1000, 1300, 1600, 1800, 2000]
for category in range(len(amazon_categories)):
    price_floor = category%13
    for i in range(60):
        name = f'{amazon_categories[category]} {i}'
        creator = random.randrange(1, 31)
        category_id = category + 1
        price = random.randrange(price_range[price_floor], price_range[price_floor+1])
        description1 = random.choice(descriptions)
        description2 = random.choice(descriptions)
        description = description1 + ' & ' + description2
        quantity = random.randrange(1, 15)
        item_to_update = Item(name=name,
                              category_id=category_id,
                              creator_id=creator,
                              description=description
                              )
        user = User.query.get(creator)
        user.item_inventory.append(Inventory(item=item_to_update,
                                             price=price,
                                             quantity=quantity))
        db.session.add(item_to_update)

    db.session.commit()
    print(f"************ {amazon_categories[category]} import end *************")

print("************ item import end *************")



