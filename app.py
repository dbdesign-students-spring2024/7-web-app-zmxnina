#!/usr/bin/env python3
import os
import sys
import subprocess
from datetime import datetime

from flask import Flask, request, redirect, url_for, render_template, flash, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user

import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from dotenv import load_dotenv

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
load_dotenv(override=True)  # take environment variables from .env.

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_KEY")

# # turn on debugging if in development mode
# app.debug = True if os.getenv("FLASK_ENV", "development") == "development" else False

# try to connect to the database, and quit if it doesn't work
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the selected database

    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live


@app.route("/")
def home():
    """
    Route for the home page.
    Simply returns to the browser the content of the index.html file located in the templates folder.
    """
    return render_template("index.html")

@app.route("/availability")
def availability():
    docs = db.reservations.find({}).sort( "date", 1)
    
    if len(list(db.reservations.find({"reserved": False}))) == 0:
        flash("We don't have any online availabilities at the moment. Please check back later.")

    return render_template("availability.html", docs=docs)


@app.route('/reserve/<mongoid>')
def reserve(mongoid):
    db.reservations.update_one({"_id": ObjectId(mongoid)}, {"$set": {"reserved": True}})
    
    flash('Your reservation has been received. We look forward to welcoming you!')
    return redirect(url_for('availability'))

@app.route("/menu")
def menu():
    return render_template("menu.html")

# Login
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, username):
        self.id = username

    def get_id(self):
        return self.id


@login_manager.user_loader
def user_loader(username):
    if username != "admin":
        return None

    return User(username)


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username != "admin":
        return None

    return User(username)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'adminpass':
            user = User(username)
            login_user(user)
            return redirect(url_for('admin'))
        
        error = "Invalid username or password"
        return render_template("login.html", error=error)
    
    # Handle GET request: display the login form without error message
    return render_template("login.html")


@app.route('/admin')
@login_required
def admin():
    docs = db.reservations.find({}).sort('date', 1)
    return render_template("admin.html", docs=docs)


@app.route("/create")
@login_required
def create():
    current_date = datetime.now().date()  # Get current date
    return render_template("create.html", current_date=current_date)


@app.route("/create", methods=["POST"])
@login_required
def create_availability():
    date = request.form["date"]
    time = request.form["time"]
    seat_count = request.form["seat_count"]

    # Create a new document with the data the user entered
    doc = {"date": date, "time": time, "seat_count": seat_count, "reserved": 'reserved' in request.form}
    db.reservations.insert_one(doc)  # Insert a new document

    return redirect(url_for("admin"))


@app.route("/edit/<mongoid>")
@login_required
def edit(mongoid):
    doc = db.reservations.find_one({"_id": ObjectId(mongoid)})
    return render_template("edit.html", mongoid=mongoid, doc=doc)  # Render the edit template


@app.route('/edit/<mongoid>', methods=['POST'])
@login_required
def edit_availability(mongoid):
    # Update logic
    db.reservations.update_one({"_id": ObjectId(mongoid)}, {"$set": {
        "date": request.form['date'],
        "time": request.form['time'],
        "seat_count": request.form['seat_count'],
        "reserved": 'reserved' in request.form
    }})
    return redirect(url_for('admin'))


@app.route('/delete/<mongoid>')
@login_required
def delete(mongoid):
    db.reservations.delete_one({"_id": ObjectId(mongoid)})
    return redirect(url_for('admin'))


@app.route('/logout')
def logout():
    logout_user()
    return 'Logged out'


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized', 401


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    GitHub can be configured such that each time a push is made to a repository, GitHub will make a request to a particular web URL... this is called a webhook.
    This function is set up such that if the /webhook route is requested, Python will execute a git pull command from the command line to update this app's codebase.
    You will need to configure your own repository to have a webhook that requests this route in GitHub's settings.
    Note that this webhook does do any verification that the request is coming from GitHub... this should be added in a production environment.
    """
    # run a git pull command
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    pull_output = process.communicate()[0]
    # pull_output = str(pull_output).strip() # remove whitespace
    process = subprocess.Popen(["chmod", "a+x", "flask.cgi"], stdout=subprocess.PIPE)
    chmod_output = process.communicate()[0]
    # send a success response
    response = make_response(f"output: {pull_output}", 200)
    response.mimetype = "text/plain"
    return response


@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=e)  # render the edit template


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    app.run(load_dotenv=True)
