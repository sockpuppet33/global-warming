#!/usr/bin/python3

from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from summarizer import summarize
import json
import sys

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# reading config

admin_password = None

with open("./config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)
    admin_password = config.get("admin-passwd", None)
    if "secret-key" in config:
        app.secret_key = config["secret-key"]
    else:
        print("Unable to read secret key from config")
        sys.exit(1)

if admin_password is None:
    print("Unable to read admin password from config")
    sys.exit(1)

# models

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False) # formatted using markdown
    publish_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def hr_publish_date(self): # YYYY Mon DD
        return self.publish_date.strftime("%Y %b %d")

# routes

@app.route("/")
@app.route("/articles")
def list_articles():
    articles = Article.query.all()
    return render_template("article_list.html", articles=articles)

@app.route("/article/<int:id>")
def view_article(id):
    article = Article.query.get(id)
    return render_template("article.html", article=article)

@app.route("/article/<int:id>/summarize")
def summarize_article(id):
    article = Article.query.get(id)
    num_sentences = request.args.get("n")
    return render_template("summarize.html", text=summarize(article.content, num_sentences))

# admin protected routes

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if session.get("authenticated"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        if request.form["password"] == admin_password:
            session["authenticated"] = True
            return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("admin_login"))
    return render_template("dashboard.html")

@app.route("/admin-new-article", methods=["GET", "POST"])
def new_article():
    if not session.get("authenticated"):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        article = Article(title=request.form["article_title"], content=request.form["article_content"])
        db.session.add(article)
        db.session.commit()
        return redirect(url_for("list_articles"))
    return render_template("new_article.html")

if __name__ == "__main__":
    app.run(debug=True)
