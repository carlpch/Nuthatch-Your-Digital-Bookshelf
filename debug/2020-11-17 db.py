from app import db
from models import User, Book

bobofish = User.query.get(1)
bobofish.check_latest()

b = bobofish.user_books()


# this line replicates the wrong shelf
[(i.timestamp, i.title) for i in b.order_by(Book.timestamp.asc()).all()][:5]

# this line replicates the wrong shelf
[(i.timestamp, i.title)  for i in b.order_by(Book.timestamp.desc()).all()][-5:]

[(i.timestamp, i.title)  for i in b.order_by(Book.timestamp.desc()).all()][:5]




Book.query.filter(Book.user_id == self.username) 

Book.query.filter(Book.user_id == 'bobofish', Book.zotero_key == 'ddd')


Book.query.order_by(Book.timestamp.desc()).first().timestamp