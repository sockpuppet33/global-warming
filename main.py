#!/usr/bin/python3

from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from sqlalchemy.ext.mutable import MutableList
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from summarizer import summarize
import json
import sys
import user_validator

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

migrate = Migrate(app, db)

# reading config

admin_password = None
quiz = None

with open("./config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    admin_password = config.get("admin-passwd", None)
    if "secret-key" in config:
        app.secret_key = config["secret-key"]
    else:
        print("Unable to read secret key from config")
        sys.exit(1)

with open("./quizconfig.json", "r", encoding="utf-8") as quiz_file:
    quiz = json.load(quiz_file)

if admin_password is None:
    print("Unable to read admin password from config")
    sys.exit(1)

# login manager

login_manager = LoginManager(app)
login_manager.login_view = "login";

# models

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False) # formatted using markdown
    publish_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def hr_publish_date(self): # YYYY Mon DD
        return self.publish_date.strftime("%Y %b %d")
    
    def is_bookmarked(self, user):
        if not hasattr(user, "bookmarks"):
            return False
        return self.id in user.bookmarks

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), nullable=False)
    passwd_hash = db.Column(db.String(256), nullable=False)
    bookmarks = db.Column(MutableList.as_mutable(db.JSON), default=list, nullable=False)

    def set_pasword(self, password):
        self.passwd_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.passwd_hash, password)

# routes

# article routes

@app.route("/")
@app.route("/articles")
def list_articles():
    articles = Article.query.all()
    return render_template("article_list.html", articles=articles)

@app.route("/article/<int:id>")
def view_article(id):
    article = Article.query.get(id)
    return render_template("article.html", article=article, is_bookmarked=article.is_bookmarked(current_user))

@app.route("/article/<int:id>/summarize")
def summarize_article(id):
    article = Article.query.get(id)
    num_sentences = int(request.args.get("n"))
    return render_template("summarize.html", text=summarize(article.content, num_sentences), article_id=id, article_title=article.title, num_sentences=num_sentences)

# user routes

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        signup_error = ""
        if not user_validator.validate_username(request.form["username"]):
            signup_error = "invalid username"
        elif not user_validator.validate_password(request.form["password"]):
            signup_error = "weak password"
        if signup_error:
            return render_template("signup.html", error=signup_error)
        else:
            user = User(name=request.form["username"])
            user.set_pasword(request.form["password"])
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("login"))
    return render_template("signup.html")

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route("/login", methods=["GET", "POST"])
def login():
    fail = False
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(name=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("list_articles"))
        else:
            fail = True
    return render_template("login.html", fail=fail)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("list_articles"))

@app.route("/bookmarks")
@login_required
def view_bookmarks():
    ids = current_user.bookmarks or []
    if not ids:
        return render_template("bookmarks.html", bookmarks=[])
    bookmarks = Article.query.filter(Article.id.in_(ids)).all()
    print(bookmarks)
    return render_template("bookmarks.html", bookmarks=bookmarks)

@app.route("/add_bookmark/<int:id>")
@login_required
def add_bookmark(id):
    user = User.query.get(current_user.id)
    user.bookmarks = user.bookmarks + [id]
    db.session.commit()
    article = Article.query.get(id)
    return render_template("add_bookmark.html", article=article)

@app.route("/del_bookmark/<int:id>")
@login_required
def del_bookmark(id):
    user = User.query.get(current_user.id)
    if id in user.bookmarks:
        user.bookmarks.remove(id)
    db.session.commit()
    article = Article.query.get(id)
    return render_template("del_bookmark.html", article=article)

# quiz routes

@app.route("/quiz/<int:q>")
def quiz_route(q):
    correct = 0
    if request.args.get("c") is not None:
        correct = int(request.args.get("c"))
    question = quiz["questions"][q]
    return render_template("quiz.html", qn=q, question=question, correct=correct)

# admin protected routes

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if session.get("authenticated"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        if request.form["password"] == admin_password:
            session["authenticated"] = True
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/admin_login.html")

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("admin_login"))
    return render_template("admin/dashboard.html")

@app.route("/admin-new-article", methods=["GET", "POST"])
def new_article():
    if not session.get("authenticated"):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        article = Article(title=request.form["article_title"], content=request.form["article_content"])
        db.session.add(article)
        db.session.commit()
        return redirect(url_for("list_articles"))
    return render_template("admin/new_article.html")

@app.route("/admin-edit-article/<int:id>", methods=["GET", "POST"])
def edit_article(id):
    if not session.get("authenticated"):
        return redirect(url_for("admin_login"))
    article = Article.query.filter_by(id=id).first()
    if request.method == "POST":
        new_title = request.form["new_title"]
        new_content = request.form["new_content"]
        article.title = new_title
        article.content = new_content
        db.session.commit()
        return redirect(url_for("view_article", id=id))
    return render_template("admin/edit_article.html", article=article, id=id)

@app.route("/admin-delete-article/<int:id>", methods=["GET", "POST"])
def delete_article(id):
    if not session.get("authenticated"):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        Article.query.filter_by(id=id).delete()
        db.session.commit()
        return redirect(url_for("list_articles"))
    return render_template("admin/delete_article.html", id=id)

if __name__ == "__main__":
    app.run(debug=True)
