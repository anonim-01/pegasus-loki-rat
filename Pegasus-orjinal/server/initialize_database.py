from models import db
from flask import Flask
from loki import app  # Import the app from loki.py

# Create a function to initialize the database
def initialize_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()
        print("Initialized the database.")

if __name__ == "__main__":
    initialize_database()
