from faker import Faker
from MiniAmazon import db
from MiniAmazon.models import User
fake = Faker()
password = "123_q"
for i in range(30):
    user = User(name=fake.name(),
                email=fake.email(),
                address=fake.address(),
                password_plain=password,
                balance=10000.0
                )
    print(user)
    db.session.add(user)
db.session.commit()