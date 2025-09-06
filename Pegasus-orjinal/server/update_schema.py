from models import db

# Create a function to update the database schema
def update_schema():
    # Add new columns to the agents table
    db.session.execute("ALTER TABLE agents ADD COLUMN last_seen DATETIME;")
    db.session.execute("ALTER TABLE agents ADD COLUMN status VARCHAR(20) DEFAULT 'offline';")
    db.session.commit()

if __name__ == "__main__":
    update_schema()
    print("Database schema updated successfully.")
