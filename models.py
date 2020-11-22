from datetime import datetime
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from pyzotero import zotero
from book import get_authors, localized_author_name, get_language
from dateutil.parser import parse


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
		"""returns a query item for pagination"""
		return Book.query.filter(Book.user_id == self.username) 

	def has_books(self):
		"""Quick check if a user has any books"""
		return True if len(Book.query.filter(Book.user_id == self.username)) > 0 else False

	def dup_item(self, z_id):
		"""
		Takes a book's Zotero ID in string, and returns the "Book" instance if the book is already in a user's data.
		The outbook is a object instance rather than True because if dup, will use db.session.delete(dup) to remove the old duplicated item.
		Returning 'dup' is quite handy this way.
		"""
		dup = self.user_books().filter(Book.zotero_key == z_id).first()
		return dup if dup else None

	def check_latest(self):
		"""
		Returns the latest time when a user modified her book.
		This is intended to serve as a check against data flow from Zotero API
		"""
		return self.user_books().order_by(Book.timestamp.desc()).first().timestamp

	def new_zotero_items(self, zotero_datetime):
		"""
		given a Zotero query result, return true of the latest Zotero item is newer than the latest database item
		"""
		return True if (zotero_datetime > self.check_latest) else False

	def zotero_connect(self):
		zotero_conn = zotero.Zotero(self.zotero_userid, 'user', self.zoter_api)
		latest_version = int(zotero_conn.last_modified_version())
		return zotero_conn, latest_version

	def zotero_full_sync(self, db):
		zotero_conn, latest_version = self.zotero_connect()
		zotero_books = zotero_conn.everything(zotero_conn.items(itemType='book'))
		zotero_books = [i['data'] for i in zotero_books]
		print('we found {} books in your Zotero. You have {} in Nuthatch.'.format(len(zotero_books), len(self.user_books().all())))

		for i in zotero_books:

			if self.dup_item(i['key']):
				dup = self.dup_item(i['key'])
				db.session.delete(dup)
				db.session.commit()

			new_book = Book(
				zotero_key = i['key'],
				title = i['title'],
				author = get_authors(i),
				publisher = i['publisher'],
				year= i['date'],
				isbn= i['ISBN'], 
				language = get_language(i),
				user_id = self.username,
				timestamp = parse(i['dateModified'])
				)

			db.session.add(new_book)
			db.session.commit()

		self.zotero_sync_version = latest_version
		db.session.commit()

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