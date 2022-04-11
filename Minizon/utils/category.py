from MiniAmazon import db
from MiniAmazon.models import Category, Item
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

# print("******** category import start ********")
#
# for c in amazon_categories:
#     print(f"importing category: {c}")
#     db.session.add(Category(name=c))
#
# db.session.commit()
# print("******** category import end ********")


descriptions = []
with open('descriptions.txt') as f:
    word = f.readline()
    while word:
        descriptions.append(word[:-1])
        word = f.readline()
    f.close()

print("************ item import start *************")

for category in range(len(amazon_categories)):
    for i in range(100):
        name = f'{amazon_categories[category]} {i}'
        creator = random.randrange(1, 34)
        category_id = category + 1
        description1 = random.choice(descriptions)
        description2 = random.choice(descriptions)
        description = description1 + ' & ' + description2
        item_to_update = Item(name=name,
                              category_id=category_id,
                              creator_id=creator,
                              description=description
                              )
        db.session.add(item_to_update)

    db.session.commit()
    print(f"************ {amazon_categories[category]} import end *************")

print("************ item import end *************")



