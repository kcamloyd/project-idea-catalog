#!usr/bin/env python3
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


# Create table of users for in-app authorization
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


# Create table of projects with name and description
class Project(Base):
    __tablename__ = 'project'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(250))

    @property
    def serialize(self):
        '''Return object data in serializable format for JSON'''
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }


# Create table of supplies with name, description, price, and link to project
class SupplyItem(Base):
    __tablename__ = 'supply'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(250))
    price = Column(String(8))
    project_id = Column(Integer, ForeignKey('project.id'))
    project = relationship(Project)

    @property
    def serialize(self):
        '''Return object data in serializable format for JSON'''
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
        }


# Following lines stay at the bottom of file:
engine = create_engine('sqlite:///projectsupplies.db')
Base.metadata.create_all(engine)
