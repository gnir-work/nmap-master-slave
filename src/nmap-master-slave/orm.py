from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, DateTime, Float
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

DB_URL = URL(drivername='mysql+pymysql', username='test', password='mypass', host='192.168.1.16',
             port=3306, database='NmapScans')
Base = declarative_base()


class NmapScan(Base):
    __tablename__ = 'nmap_scan'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(16))
    start_time = Column(DateTime)
    elapsed = Column(Float)
    status = Column(String(32))
    ports = relationship("PortScan", back_populates="npm_scan")


class PortScan(Base):
    __tablename__ = 'port_scan'
    id = Column(Integer, primary_key=True)
    port = Column(Integer)
    npm_scan_id = Column(Integer, ForeignKey('nmap_scan.id'))
    npm_scan = relationship("NmapScan", back_populates="ports")
    state = Column(String(32))
    name = Column(String(64))
    reason = Column(String(64))
    product = Column(String(64))
    version = Column(String(32))
    protocol = Column(String(32))
    method = Column(String(32))


engine = create_engine(DB_URL)
Base.metadata.create_all(engine)
