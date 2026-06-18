from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

dotenv_path = os.getenv("ETL_DOTENV_PATH")

if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
else:
    engine = None

    def SessionLocal():
        raise RuntimeError(
            "DATABASE_URL is not configured. Add a .env file with DATABASE_URL "
            "next to the exe or in the project directory."
        )
