#!/usr/bin/python3

from main import app, db

app.app_context().push()
db.create_all()
print("database created")
