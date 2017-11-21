#!usr/bin/env python3
from flask import Flask, render_template, request, url_for
from flask import redirect, jsonify, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Project, SupplyItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

# Connect to database and create new session
engine = create_engine('sqlite:///projectsupplies.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Read OAuth2 data
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Project Catalog"


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


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
    url = 'https://www.googleapis.com/oauth2/v1/'
    url += 'tokeninfo?access_token={}'.format(access_token)
    h = httplib2.Http()
    hRequest = h.request(url, 'GET')[1]
    result = json.loads(hRequest.decode())
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

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
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
                    json.dumps(
                        'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 150px; height: 150px;'
    output += 'border-radius: 75px; -webkit-border-radius: 75px;'
    output += '-moz-border-radius: 75px;"> '
    flash("you are now logged in")
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(
                email=login_session['email'],
                picture=login_session['picture'])
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
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/'
    url += 'revoke?token={}'.format(access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('showProjects'))
    else:
        response = make_response(json.dumps(
                                    'Failed to revoke token ' +
                                    'for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Return JSON for each project
@app.route('/project/JSON/')
def projectJSON():
    projects = session.query(Project).all()
    return jsonify(projects=[p.serialize for p in projects])


# Return JSON for each list of supplies
@app.route('/project/<int:project_id>/supplies/JSON/')
def projectSuppliesJSON(project_id):
    project = session.query(Project).filter_by(id=project_id).one()
    items = session.query(SupplyItem).filter_by(project_id=project_id).all()
    return jsonify(SupplyItems=[i.serialize for i in items])


# Return JSON for each individual supply item
@app.route('/project/<int:project_id>/supplies/<int:supply_id>/JSON/')
def supplyItemJSON(project_id, supply_id):
    supply = session.query(SupplyItem).filter_by(id=supply_id).one()
    return jsonify(supply=supply.serialize)


# Show all projects
@app.route('/')
@app.route('/project/')
def showProjects():
    projects = session.query(Project).all()
    if 'email' not in login_session:
        return render_template('publicProjects.html', projects=projects)
    else:
        return render_template(
                'projects.html', projects=projects,
                creator=login_session['user_id'])


# Create a new project
@app.route('/project/new/', methods=['GET', 'POST'])
def newProject():
    if 'email' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newProject = Project(
            name=request.form['name'],
            description=request.form['description'],
            user_id=login_session['user_id'])
        session.add(newProject)
        session.commit()
        return redirect(url_for('showProjects'))
    else:
        return render_template('newProject.html')


# Edit an existing project
@app.route('/project/<int:project_id>/edit/', methods=['GET', 'POST'])
def editProject(project_id):
    editedProject = session.query(Project).filter_by(id=project_id).one()
    if 'email' not in login_session:
        return redirect('/login')
    if editedProject.user_id != login_session['user_id']:
        flash('You can only edit a project you created')
        return redirect(url_for('showProjects', project_id=project_id))
    if request.method == 'POST':
        if request.form['name']:
            editedProject.name = request.form['name']
        if request.form['description']:
            editedProject.description = request.form['description']
        session.add(editedProject)
        session.commit()
        return redirect(url_for('showProjects'))
    else:
        return render_template('editProject.html', project=editedProject)


# Delete a project
@app.route('/project/<int:project_id>/delete/', methods=['GET', 'POST'])
def deleteProject(project_id):
    projectToDelete = session.query(Project).filter_by(id=project_id).one()
    if 'email' not in login_session:
        return redirect('/login')
    if projectToDelete.user_id != login_session['user_id']:
        flash('You can only delete a project you created')
        return redirect(url_for('showProjects', project_id=project_id))
    if request.method == 'POST':
        session.delete(projectToDelete)
        session.commit()
        return redirect(url_for('showProjects', project_id=project_id))
    else:
        return render_template('deleteProject.html', project=projectToDelete)


# Show all supplies needed for a given project
@app.route('/project/<int:project_id>/')
@app.route('/project/<int:project_id>/supplies/')
def showSupplies(project_id):
    project = session.query(Project).filter_by(id=project_id).one()
    creator = getUserInfo(project.user_id)
    supplies = session.query(SupplyItem).filter_by(project_id=project_id).all()
    if 'email' not in login_session or creator.id != login_session['user_id']:
        return render_template(
                'publicSupplies.html',
                supplies=supplies,
                project=project)
    else:
        return render_template(
                'supplies.html',
                supplies=supplies,
                project=project)


# Create a new supply item
@app.route('/project/<int:project_id>/supply/new/', methods=['GET', 'POST'])
def newSupplyItem(project_id):
    if 'email' not in login_session:
        return redirect('/login')
    project = session.query(Project).filter_by(id=project_id).one()
    if project.user_id != login_session['user_id']:
        flash('You cannot add a supply item to a project you did not create')
        return redirect(url_for('showSupplies', project_id=project_id))
    if request.method == 'POST':
        newItem = SupplyItem(
            name=request.form['name'],
            description=request.form['description'],
            price=request.form['price'],
            project_id=project_id,
            user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        return redirect(url_for('showSupplies', project_id=project_id))
    else:
        return render_template('newSupply.html', project_id=project_id)


# Edit an existing supply item
@app.route(
    '/project/<int:project_id>/supply/<int:supply_id>/edit/',
    methods=['GET', 'POST'])
def editSupplyItem(project_id, supply_id):
    if 'email' not in login_session:
        return redirect('/login')
    editedItem = session.query(SupplyItem).filter_by(id=supply_id).one()
    project = session.query(Project).filter_by(id=project_id).one()
    if project.user_id != login_session['user_id']:
        flash('You cannot edit a supply item you did not create')
        return redirect(url_for('showSupplies', project_id=project_id))
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['name']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('showSupplies', project_id=project_id))
    else:
        return render_template(
                'editSupply.html', project_id=project_id,
                supply_id=supply_id, item=editedItem)


# Delete a supply item
@app.route(
    '/project/<int:project_id>/supply/<int:supply_id>/delete/',
    methods=['GET', 'POST'])
def deleteSupplyItem(project_id, supply_id):
    if 'email' not in login_session:
        return redirect('/login')
    project = session.query(Project).filter_by(id=project_id).one()
    itemToDelete = session.query(SupplyItem).filter_by(id=supply_id).one()
    if project.user_id != login_session['user_id']:
        flash('You cannot delete a supply item you did not create')
        return redirect(url_for('showSupplies', project_id=project_id))
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('showSupplies', project_id=project_id))
    else:
        return render_template(
            'deleteSupply.html', project_id=project_id,
            supply_id=supply_id, item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'sdfoikI8830923SDOIJjsdk4klkj342ij*(DUFJ#)'
    # REMOVE APP.DEBUG FOR PRODUCTION
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
