import sys
import os
from flask import Flask
from models import db

# Add server directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app from loki.py
from loki import app  

# Create a function to initialize the database
def initialize_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()
        print("Initialized the database.")

if __name__ == "__main__":
    initialize_database()
