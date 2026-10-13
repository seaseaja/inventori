import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://root:021936@localhost:3306/db_inventori"
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session