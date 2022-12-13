from main import db, User, Item
from  werkzeug.security import generate_password_hash

user1 = User(email = 'yt2777@columbia.edu', password = generate_password_hash('password'), admin=True)
user2 = User(email = 'ab1234@columbia.edu', password = generate_password_hash('password'), admin=False)
user3 = User(email = 'AB4321@columbia.edu', password = generate_password_hash('password'), admin=False)

item1_1 = Item(id = 'product_set1/0986800006', uid=1, count=2, detail='')
item2_1 = Item(id = 'product_set1/1108022007', uid=1, count=1, detail='')
item1_2 = Item(id = 'product_set1/0986800006', uid=2, count=3, detail='')

db.drop_all()
db.create_all()

db.session.add_all([user1, user2, user3])
db.session.add_all([item1_1, item2_1, item1_2])

db.session.commit()