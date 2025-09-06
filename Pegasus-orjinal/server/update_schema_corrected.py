from models import db
from flask import Flask
from sqlalchemy import text

# Create a Flask application instance
app = Flask(__name__)

# Create a function to update the database schema
def update_schema():
    with app.app_context():
        # Add new columns to the agents table
        db.session.execute(text("ALTER TABLE agents ADD COLUMN last_seen DATETIME;"))
        db.session.execute(text("ALTER TABLE agents ADD COLUMN status VARCHAR(20) DEFAULT 'offline';"))
        db.session.commit()

if __name__ == "__main__":
    update_schema()
    print("Database schema updated successfully.")
