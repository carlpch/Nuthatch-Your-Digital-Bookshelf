# from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, BooleanField, SubmitField
# from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
# from models import User
from pyzotero import zotero
from rauth import OAuth1Service
from flask import session, flash, url_for, redirect

zoteroAuth = OAuth1Service(
        name='zotero',
        consumer_key='7e808de4b1f9ca43177f',
        consumer_secret='805a84c668cb0920739b',
        request_token_url='https://www.zotero.org/oauth/request',
        access_token_url='https://www.zotero.org/oauth/access',
        authorize_url='https://www.zotero.org/oauth/authorize',
        base_url='https://api.zotero.org')

request_token = ''
request_token_secret = ''

def get_auth_url():
	request_token, request_token_secret = zoteroAuth.get_request_token()
	session['request_token'] = request_token
	session['request_token_secret'] = request_token_secret
	auth_url = zoteroAuth.get_authorize_url(request_token)
	return auth_url

def get_authors(i):
    author_number = len(i['creators'])
    author_list = i['creators']
    language = i['language']
    creators = i['creators']
    output = str()
    n = 0

    if author_number > 0:  # some titles may not have author/creators at all
        while n + 1 < author_number:
            if 'name' in author_list[n].keys():
                output += author_list[n]['name']
            else:
                output += localized_author_name(
                    first=author_list[n].get('firstName'),
                    last=author_list[n].get('lastName'),
                    language=language)

            output += ', '
            n += 1
        if 'name' in author_list[n].keys():
            output += author_list[n]['name']
        else:
            output += localized_author_name(
                first=author_list[n].get('firstName'),
                last=author_list[n].get('lastName'),
                language=language)
    return output


def get_cover(b):
    has_cover = False
    parent_key = b['key']
    children = zot.children(parent_key)
    short_pdf_path = str()
    book_cover_key = 'DEFAULT'
    for child in children:
        if has_cover == False:
            print('No cover yet')
            book_cover_key = 'DEFAULT'  # the DEFAULT parent_key is DEFAULT
            if child['data']['itemType'] == 'attachment':
                try:
                    attachment_file = child['data']['filename']
                    if ".pdf" in attachment_file:
                        attachment_key = child['data']['key']
                        attachment_path = "/Users/Carl/Juris-M/storage/{}/{}".format(attachment_key, attachment_file)
                        print(attachment_path)
                        jpg_path = '//Applications/MAMP/htdocs/hummingbird/_covers/{}.jpg'.format(parent_key)
                        if os.path.exists(jpg_path):
                            book_cover_key = parent_key
                            short_pdf_path = "storage/{}/{}".format(attachment_key, attachment_file)
                            print("Book cover already generated in JPEG.")
                            has_cover = True
                        else:
                            try:
                                with tempfile.TemporaryDirectory() as path:
                                    images_from_path = convert_from_path(attachment_path, first_page=1, last_page=1, fmt="jpeg", output_folder=path)
                                    images_from_path[0].save(jpg_path)
                                    book_cover_key = parent_key
                                    short_pdf_path = "storage/{}/{}".format(attachment_key, attachment_file)
                                    has_cover = True
                            except:
                                print("Unable to find PDF file(s)")
                                missing_pdf.append(b['title'])
                    else:
                        no_attachment.append(b['title'])
                except KeyError:
                    pass
        else:
            print('Skipping this attachment because book cover is already obtained.')
    return book_cover_key, short_pdf_path


def localized_author_name(first, last, language):
    first = str(first)
    last = str(last)
    if language in ['ja', 'jp', 'Japanese', '日本語']:
        author = last + ' ' + first
    elif language in ['zh', 'zh-TW', 'Traditional Chinese']:
        author = last + first
    else:
        author = first + ' ' + last
    return author


def get_language(item):
    clean_language = 'en'
    item = item['language']
    if item in ['ja', 'jp', 'Japanese', '日本語']:
        clean_language = 'ja'
    elif item in ['zh', 'zh-TW', 'Traditional Chinese']:
        clean_language = 'zh-TW'
    elif item in ['kor', 'Korean']:
        clean_language = 'kor'
    return clean_language
