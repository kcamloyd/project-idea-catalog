#!usr/bin/env python3
from flask import Flask, render_template, request, url_for, redirect, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

engine = create_engine('sqlite:///projectsupplies.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


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
@app.route('/projects/')
def showProjects():
    projects = session.query(Project).all()
    return render_template('projects.html', projects=projects)


# Create a new project
@app.route('/project/new/', methods=['GET', 'POST'])
def newProject():
    if request.method == 'POST':
        newProject = Project(
            name=request.form['name'],
            description=request.form['description'])
        session.add(newProject)
        session.commit()
        return redirect(url_for('showProjects'))
    else:
        return render_template('newProject.html')


# Edit an existing project
@app.route('/project/<int:project_id>/edit/', methods=['GET', 'POST'])
def editProject(project_id):
    editedProject = session.query(Project).filter_by(id=project_id).one()
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
    supplies = session.query(SupplyItem).filter_by(project_id=project_id).all()
    return render_template('supplies.html', supplies=supplies, project=project)


# Create a new supply item
@app.route('/project/<int:project_id>/supply/new/', methods=['GET', 'POST'])
def newSupplyItem(project_id):
    if request.method == 'POST':
        newItem = SupplyItem(
            name=request.form['name'],
            description=request.form['description'],
            price=request.form['price'],
            project_id=project_id)
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
    editedItem = session.query(SupplyItem).filter_by(id=supply_id).one()
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
            'editSupply.html',
            project_id=project_id,
            supply_id=supply_id,
            item=editedItem)


# Delete a supply item
@app.route(
    '/project/<int:project_id>/supply/<int:supply_id>/delete/',
    methods=['GET', 'POST'])
def deleteSupplyItem(project_id, supply_id):
    itemToDelete = session.query(SupplyItem).filter_by(id=supply_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('showSupplies', project_id=project_id))
    else:
        return render_template(
            'deleteSupply.html', project_id=project_id,
            supply_id=supply_id, item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = '\xdaH)\x92\DSxf2\xb1\xe0\x*#b4$\x1aYH\xc?8t\x88\x08\x04'
    # REMOVE APP.DEBUG FOR PRODUCTION
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
