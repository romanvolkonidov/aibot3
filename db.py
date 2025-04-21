# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, LargeBinary, BigInteger, ForeignKey
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    context = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProject(Base):
    __tablename__ = "user_projects"
    user_id = Column(BigInteger, ForeignKey('users.user_id'), primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    is_current = Column(Boolean, default=False)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    role = Column(String(20), nullable=False)
    content = Column(Text(length=16777215), nullable=False)  # MEDIUMTEXT in MySQL
    created_at = Column(DateTime, default=datetime.utcnow)

class ProjectFile(Base):
    __tablename__ = "project_files"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    filename = Column(String(255), nullable=False)
    content = Column(LargeBinary)
    mime_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)

    # At end of db.py
if __name__ == '__main__':
    init_db()