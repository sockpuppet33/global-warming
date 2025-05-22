#!/usr/bin/python3

from main import db, app, Article
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("title", type=str)
parser.add_argument("content", type=str)
args = parser.parse_args()

with app.app_context():
    article = Article(title=args.title, content=args.content)
    db.session.add(article)
    db.session.commit()

print("created new test article")
