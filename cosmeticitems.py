from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, relation, backref
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):

    __tablename__ = 'user'

    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    id = Column(Integer, primary_key=True)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
            'email': self.email,
        }


class Genre(Base):

    __tablename__ = 'genre'

    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

# We added this serialize function to be able to send JSON objects in a
# serializable format
    @property
    def serialize(self):

        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
        }


class Item(Base):

    __tablename__ = 'item'

    name = Column(String(30), nullable=False)
    description = Column(String(250))
#    developer = Column(String(80))
#    release = Column(String(20))
    id = Column(Integer, primary_key=True)
    genre_id = Column(Integer, ForeignKey('genre.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    #genre = relationship(Genre)
    genre = relation(
        'Genre',
        uselist=False,
        backref=backref(
            'items',
            uselist=True,
            cascade='all, delete-orphan',),)
    user = relationship(User)

# We added this serialize function to be able to send JSON objects in a
# serializable format
    @property
    def serialize(self):

        return {
            'name': self.name,
            'id': self.id,
            'description': self.description,
            'genre_id': self.genre_id,
            'user_id': self.user_id,
        }


# insert at end of file

engine = create_engine('sqlite:///cosmeticitems.db')
Base.metadata.create_all(engine)
