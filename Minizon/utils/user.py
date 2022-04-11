from faker import Faker
from MiniAmazon import db
from MiniAmazon.models import User
import random
fake = Faker()
password = "123_q"
for i in range(30):
    balance = random.randrange(1000, 10000)
    user = User(name=fake.name(),
                email=fake.email(),
                address=fake.address(),
                password_plain=password,
                balance=balance
                )
    print(user)
    db.session.add(user)
db.session.commit()