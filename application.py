from flask import Flask, render_template, request, redirect,\
    url_for, flash, jsonify
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from cosmeticitems import Base, Genre, Item, User
from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
# from oauth2client.client import AccessTokenCredentials
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Game Category Application"

# Connect to Database and create database session
engine = create_engine('sqlite:///cosmeticitems.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_' \
          'exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s'\
          % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]
    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly
    # logout, let's strip out the information before the equals sign in
    # our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=' \
          '200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
          % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already '
                                            'connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: ' \
              '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only a connected user
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Execute HTTP GET request to revoke current token
    access_token = login_session.get('credentials')
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % credentials
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] != '200':
        response = make_response(json.dumps('Failed to revoke token for '
                                            'given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Genres and Items Information
@app.route('/users/JSON')
def showUsersJSON():
    users = session.query(User)
    return jsonify(Users=[i.serialize for i in users])


@app.route('/genres/JSON')
def showGenresJSON():
    genre = session.query(Genre)
    return jsonify(Genres=[i.serialize for i in genre])


@app.route('/genre/<int:genre_id>/items/JSON')
def showItemsJSON(genre_id):
    genre = session.query(Genre).filter_by(id=genre_id).one()
    items = session.query(Item).filter_by(genre_id=genre_id).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/genre/<int:genre_id>/item/<int:item_id>/JSON')
def ItemJSON(genre_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=item.serialize)


# "This page will show baby genres"
@app.route('/')
@app.route('/genres')
def showGenres():
    genrelist = session.query(Genre).order_by(asc(Genre.name))
    if 'username' not in login_session:
        return render_template('publicgenres.html', genrelist=genrelist)
    else:
        return render_template('genres.html', genrelist=genrelist)


# "This page will be for making a new genre"
@app.route('/genre/new', methods=['GET', 'POST'])
def newGenre():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newGenre = Genre(
            name=request.form['name'],
            # description=request.form['description'],
            user_id=login_session['user_id'])
        session.add(newGenre)
        session.commit()
        flash("New Genre %s Successfully Created!" % newGenre.name)
        return redirect(url_for('showGenres'))
    else:
        return render_template('newGenre.html')


# "This page will be editing genre %s" %genre_id
@app.route('/genre/<int:genre_id>/edit', methods=['GET', 'POST'])
def editGenre(genre_id):
    editedGenre = session.query(Genre).filter_by(id=genre_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedGenre.user_id != login_session['user_id']:
        return render_template('uneditable.html')
    if request.method == 'POST':
        if request.form['name']:
            editedGenre.name = request.form['name']
        session.add(editedGenre)
        session.commit()
        flash("Genre Successfully Edited!")
        return redirect(url_for('showGenres'))
    else:
        return render_template('editGenre.html', genre_id=genre_id,
                               i=editedGenre)


# "This page will be deleting genre %s" %genre_id
@app.route('/genre/<int:genre_id>/delete', methods=['GET', 'POST'])
def deleteGenre(genre_id):
    deleteGenre = session.query(Genre).filter_by(id=genre_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if deleteGenre.user_id != login_session['user_id']:
        return render_template('uneditable.html')
# "<script>function myFunction() {alert('You are not " \
#  "authorized to delete this genre. Please create your " \
# "own genre in order to delete.');}</script><body " \
# "onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(deleteGenre)
        session.commit()
        flash("Genre Successfully Deleted!")
        return redirect(url_for('showGenres'))
    else:
        return render_template('deleteGenre.html', genre_id=genre_id,
                               i=deleteGenre)


# "This page will show items for genre %s" %genre_id
@app.route('/genre/<int:genre_id>')
@app.route('/genre/<int:genre_id>/items')
def showItems(genre_id):
    genre = session.query(Genre).filter_by(id=genre_id).one()
    creator = getUserInfo(genre.user_id)
    items = session.query(Item).filter_by(genre_id=genre.id)
    if 'username' not in login_session or creator.id != \
            login_session['user_id']:
        return render_template('publicitems.html', items=items,
                               genre=genre, creator=creator)
    else:
        return render_template('items.html', genre=genre,
                               items=items, creator=creator)


# "This page is for making a new item for genre %s" %genre_id
@app.route('/genre/<int:genre_id>/item/new', methods=['GET', 'POST'])
def newItem(genre_id):
    if 'username' not in login_session:
        return redirect('/login')
    genre = session.query(Genre).filter_by(id=genre_id).one()
    if request.method == 'POST':
        newItem = Item(
            name=request.form['name'], description=request.form['description'],
            # developer=request.form['developer'],
            # release=request.form['release'],
            genre_id=genre_id, user_id=genre.user_id)
        session.add(newItem)
        session.commit()
        flash("New Item Created!")
        return redirect(url_for('showItems', genre_id=genre_id))
    else:
        return render_template('newItem.html', genre_id=genre_id)


# "This page is for editing item %s" %item_id
@app.route('/genre/<int:genre_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(genre_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
#        if request.form['developer']:
#            editedItem.developer = request.form['developer']
#        if request.form['release']:
#            editedItem.release = request.form['release']
        session.add(editedItem)
        session.commit()
        flash("Item Successfully Edited!")
        return redirect(url_for('showItems', genre_id=genre_id))
    else:
        return render_template('editItem.html', genre_id=genre_id,
                               item_id=item_id, i=editedItem)


# "This page is for deleting item %s" %item_id
@app.route('/genre/<int:genre_id>/item/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(genre_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    deleteItem = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        flash("Item Successfully Deleted!")
        return redirect(url_for('showItems', genre_id=genre_id))
    else:
        return render_template('deleteItem.html', genre_id=genre_id,
                               item_id=item_id, i=deleteItem)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showGenres'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showGenres'))

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
