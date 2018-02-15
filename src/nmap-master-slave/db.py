from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from orm import Base, DB_URL

engine = create_engine(DB_URL)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


def get_session():
    """
    Returns a new session with the db.
    :return sqlalchemy.orm.session.Session: The session with the db
    """
    return DBSession()
