# init_db.py
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base  # your package

# --- 1) Create SQLite database ---
DATABASE_URL = "sqlite:///data/metrology.db"  # file in root folder
engine = create_engine(DATABASE_URL, echo=True)  # echo=True shows SQL statements

# --- 2) Create all tables ---
Base.metadata.create_all(engine)

# --- 3) Print all tables ---
inspector = inspect(engine)
tables = inspector.get_table_names()
print("Tables created in database:")
for table in tables:
    print(f"- {table}")

# --- 4) Optional: create a session to test ---
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
print("Session created successfully:", session)
session.close()