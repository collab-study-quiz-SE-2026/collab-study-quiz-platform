import os

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

database_url = URL.create(
    "postgresql+psycopg",
    username=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    host=os.getenv("PGHOST", "127.0.0.1"),
    port=int(os.getenv("PGPORT", "5432")),
    database=os.environ["PGDATABASE"],
)

engine = create_engine(database_url, connect_args={"connect_timeout": 3})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass
