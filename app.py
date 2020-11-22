# imports
import sqlite3
import math
import pandas as pd
from flask import Flask, request, session, g, redirect, url_for, \
                  abort, render_template, flash, jsonify
from rauth import OAuth1Service
from rauth.utils import parse_utf8_qsl 
from tornado.web import HTTPError # unknown
from pyzotero import zotero
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
import book # book.py
from book import get_authors, localized_author_name, get_language
from flask_bootstrap import Bootstrap
from datetime import datetime
import json 
from dateutil.parser import parse

# create an app instance
app = Flask(__name__)
app.config.from_object(Config)

# create a database instance
db = SQLAlchemy(app)

# create an instance of database migration class
migrate = Migrate(app,db)

login = LoginManager(app)
login.login_view = 'login'
bootstrap = Bootstrap(app)


import models
from models import User, Book
from forms import LoginForm, RegistrationForm
from explore import load_embedding, showneighbors, postgres_query, load_embedding2, find_close_books, load_bookinfo

zoteroAuth = OAuth1Service(
        name='zotero',
        consumer_key= app.config['ZOTERO_CONSUMER_KEY'],
        consumer_secret= app.config['ZOTERO_CONSUMER_SECRET'],
        request_token_url='https://www.zotero.org/oauth/request',
        access_token_url='https://www.zotero.org/oauth/access',
        authorize_url='https://www.zotero.org/oauth/authorize',
        base_url='https://api.zotero.org')
request_token = ''
request_token_secret = ''

# connect to database
def connect_db():
	rv = sqlite3.connect(app.config['DATABASE'])
	rv.row_factory = sqlite3.Row
	return rv

# open database connection
def get_db():
	if not hasattr(g, 'sqlite_db'):
		g.sqlite_db = connect_db()
	return g.sqlite_db

# create database
def init_db():
	with app.app_context():
		db = get_db()
		with app.open_resource('schema.sql', mode='r') as f:
			db.cursor().executescript(f.read())
		db.commit()

# close database connection
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return bookshelf()
    else:
        return render_template('index.html', title='Nuthatch')

@app.route('/bookshelf')
@login_required
def bookshelf():
    if current_user.zoter_api and current_user.zotero_sync_version:
        print('user has everything to use bookshelf')

        page = request.args.get('page', 1, type=int)
        books = current_user.user_books().order_by(Book.timestamp.desc())
        shelf = books.paginate(page ,app.config['POSTS_PER_PAGE'], False)

        return render_template('bookshelf.html', title='My Bookshelf', 
            booklist = shelf.items, 
            page = page, 
            lastpage = (len(current_user.user_books().all())//app.config['POSTS_PER_PAGE'])+1)

    elif current_user.zoter_api != '':
        print('user has api key but no data, going to sync. current_user.zotero_sync_version = {}'.format(current_user.zotero_sync_version))
        # flash('{}, you have Zotero authentication, but have not synced your data!'.format(current_user.username))
        return redirect(url_for('sync'))
    else:
        flash('{}, you might want to complete Zotero authentication for your books to be displayed here!'.format(current_user.username))
    return render_template('bookshelf.html', title='Nuthatch')

@app.route('/auth')
@login_required
def auth():
    """ guide a user to click on the Zotero callback link to finish Oauth authentication """

    if current_user.is_authenticated:

        # OAuth is only necesary when we don't have a user's API
        if not current_user.zoter_api:

            def get_auth_url():
                request_token, request_token_secret = zoteroAuth.get_request_token()
                session['request_token'] = request_token
                session['request_token_secret'] = request_token_secret
                auth_url = zoteroAuth.get_authorize_url(request_token)
                return auth_url

            flash('Hi! {}, please visit <a href="{}" target="new">here</a> for authentication.'.format(current_user.username, get_auth_url()))
            return redirect(url_for('bookshelf'))
        
        else:
            flash('You already have an API key!')
            return redirect(url_for('sync'))

@app.route('/auth_callback')
def auth_cb():
    if not current_user.is_authenticated:
        flash('Alert: Cannot complete authentication. User is not logged in.')
    else:
        verifier = request.args.get('oauth_verifier')
        text = 'Call back comes here, verifier is {}'.format(verifier)
        access_token_response = zoteroAuth.get_raw_access_token(
                session['request_token'], session['request_token_secret'],
                data={'oauth_verifier': verifier})
        access_info = parse_utf8_qsl(access_token_response.content)
        current_user.zotero_userid = access_info['userID']
        current_user.zotero_username = access_info['username']
        current_user.zoter_api = access_info['oauth_token_secret']
        db.session.commit()
    flash('Success! We successfullly received API key from Zoter user {}'.format(current_user.zotero_username))
    return redirect(url_for('bookshelf'))

@app.route('/login', methods = ['GET','POST'])
def login():
    if current_user.is_authenticated:
        # flash('You are already logged in, {}'.format(current_user.username))
        return redirect(url_for('bookshelf'))
    form = LoginForm()
    if form.validate_on_submit():
        # flash('Login requested for user {}, remember_me ={}'.format(
        #     form.username.data, form.remember_me.data))
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('bookshelf')
        return redirect(next_page)
    return render_template('login.html', title="Sign In", form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('bookshelf'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/sync')
@login_required
def sync():
    # 
    if current_user.zoter_api:
        try:
            _, latest_version = current_user.zotero_connect()

        except:
            print('Error, cannot connect to Zotero with user API')
            raise

        if latest_version == current_user.zotero_sync_version:
            flash('Your Zotero book data is up to date.')
            return redirect(url_for('bookshelf'))

        else:
            # flash('Updating your book data now... zot version = {}, local = {}'.format(latest_version, current_user.zotero_sync_version))
            flash('Updating your book data now...'.format(latest_version, current_user.zotero_sync_version))
            zotero_books = current_user.zotero_full_sync(db = db)
            return redirect(url_for('bookshelf'))


@app.route('/explore')
@login_required
def explore():
    if current_user.user_books():
        user_books = current_user.user_books().all()
        user_titles = [i.title for i in user_books]
        bookinfo = load_bookinfo()
        # Begin Matching
        bookinfo['matched'] = bookinfo.bookName.str.lower().isin([x.lower() for x in user_titles])
        if sum(bookinfo.matched) <1 :
            flash("Sorry! Cannot match your books to our data. ")
            return render_template('explore.html', title='Explore', emb=embedding)
        else:
            matched_books = bookinfo[bookinfo['matched']].reset_index()
            matched_books = matched_books.drop(['Unnamed: 0','index','matched'],axis=1)
            flash('Click on any of the book below to see our recommendations! 😊')
            return render_template('explore.html', title='Explore', matched_books=matched_books)
    else:
        flash('You got no books!')
        return render_template('explore.html', title='Explore')

@app.route('/recommend/<int:bookID>', methods=['GET','POST'])    #int has been used as a filter that only integer will be passed in the url otherwise it will give a 404 error
def recommend(bookID):
    title = request.args.get('title')
    embedding = load_embedding()
    bookinfo = load_bookinfo()
    results = showneighbors(bookID, embedding, bookinfo).to_html()
    flash('Here are five other books based on <em>{}</em>'.format(title))
    return render_template('recommend.html', title='Book Recommendation', results = results)


@app.route('/_get_suggestions', methods=['POST'])
def get_suggestions():
    bookID = int(request.form['bookID'])
    embedding = load_embedding()
    bookinfo = load_bookinfo()
    results = showneighbors(bookID, embedding, bookinfo)
    return results.to_json(orient='records')

@app.route('/search', methods=['GET'])
@login_required
def search():
    keyword = request.args.get('keyword')
    if current_user.zoter_api != '' and current_user.zotero_sync_version != '':
        page = request.args.get('page', 1, type=int)
        key_phrase = "%{}%".format(keyword)
        matched_books = current_user.user_books().filter(Book.title.like(key_phrase))
        results = matched_books.paginate(page ,app.config['POSTS_PER_PAGE'], False)
        return render_template('search.html', title='Search Results', 
            booklist=results.items, 
            page=page, 
            lastpage = (len(matched_books.all())//app.config['POSTS_PER_PAGE'])+1, 
            keyword = keyword)

@app.route('/demo')
def demo():
    if current_user.is_authenticated:
        return redirect(url_for('bookshelf'))
    else:
        user = User.query.filter_by(username='demo').first()
        login_user(user, remember=False)
        flash('Welcome to the demo page!')
        return redirect(url_for('bookshelf'))

@app.route('/postgres')
def postgres():
    if current_user.user_books():
        user_books = current_user.user_books().all()
        user_book_data = [{'title':i.title, 'author':i.author, 'publisher':i.publisher, 'year':i.year} for i in user_books if i.title is not None]
        user_book_data = pd.DataFrame(user_book_data)
        data = postgres_query()
        matched_books = user_book_data.merge(data[['nuthatch_id', 'title']], left_on='title', right_on='title')
        if len(matched_books) < 1:
            flash("Sorry! Cannot match your books to our data. ")
            return render_template('postgres.html', title='Postgres')
        else:
            flash('Click on any of the book below to see our recommendations! 😊')
            return render_template('postgres.html', title='Postgres', matched_books=matched_books)
    else:
        flash('You got no books!')
        return render_template('postgres.html', title='Postgres')

@app.route('/_top5', methods=['POST'])
def _top5():
    nuthatch_id = int(request.form['nuthatch_id'])
    data = postgres_query()
    candidates_emb = load_embedding2()
    top5 = find_close_books(nuthatch_id=nuthatch_id, candidates_emb=candidates_emb, data=data)
    results = [{'title':i[0], 'year':i[1]} for i in top5]
    print(results)
    return pd.DataFrame(results).to_json(orient='records')

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Book': Book}

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run()
