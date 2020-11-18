from datetime import datetime
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key = True)
	username = db.Column(db.String(64), index=True, unique=True)
	email = db.Column(db.String(120), index=True, unique=True)
	password_hash = db.Column(db.String(128))
	zotero_sync_version = db.Column(db.Integer, default='')
	zotero_username = db.Column(db.String(128), default='')
	zotero_userid = db.Column(db.String(128), default='')
	zoter_api = db.Column(db.String(128), default='')
	books = db.relationship('Book', backref='Owner', lazy='dynamic')

	def __repr__(self):
		return '<User {}>'.format(self.username)

	def set_password(self,password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)

	def user_books(self):
		#return Book.query.filter(Book.user_id == self.username).all() # returns a list
		return Book.query.filter(Book.user_id == self.username) 

	def has_books(self):
		#return Book.query.filter(Book.user_id == self.username).all() # returns a list
		return len(Book.query.filter(Book.user_id == self.username)) > 0 # returns a query item for pagination

	def dup_item(self, z_id):
		dup = Book.query.filter(Book.user_id == self.username, Book.zotero_key == z_id).first()
		if dup:
			return dup
		else:
			return None

class Book(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	zotero_key = db.Column(db.String(140), unique=True)
	title = db.Column(db.String(140))
	author = db.Column(db.String(140))
	publisher = db.Column(db.String(140))
	language = db.Column(db.String(140))
	year = db.Column(db.Integer)
	isbn = db.Column(db.Integer)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	timestamp = db.Column(db.DateTime, index=True, default = datetime.utcnow)

	def __repr__(self):
		return '<Book {}>'.format(self.title)

	


@login.user_loader
def load_user(id):
    return User.query.get(int(id))