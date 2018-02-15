from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from orm import Base, DB_URL, NmapScan
from custom_exceptions import DbException


engine = create_engine(DB_URL)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


def get_session():
    """
    Returns a new session with the db.
    :return sqlalchemy.orm.session.Session: The session with the db
    """
    return DBSession()


def get_scan_by_id(scan_id, session=None):
    session = session or get_session()
    scan = session.query(NmapScan).get(scan_id)
    if scan is None:
        raise DbException("Cant find scan {}".format(scan_id))
    else:
        session.add(scan)
        return scan