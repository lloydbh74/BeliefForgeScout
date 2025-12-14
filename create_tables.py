from src.db.connection import get_db_manager
from src.db.models import Base

def create_tables():
    db_manager = get_db_manager()
    engine = db_manager.engine
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    create_tables()
