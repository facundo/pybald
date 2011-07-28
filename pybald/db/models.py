
from sqlalchemy import (
    MetaData,
    INT as Int,
    Integer,
    Float,
    Column,
    UniqueConstraint,
    Index,
    ForeignKey,
    String,
    DateTime,
    TIMESTAMP as TimeStamp,
    PickleType,
    Time,
    Table,
    or_,
    and_,
    not_,
    select
    )

from sqlalchemy.types import (
    BLOB,
    BOOLEAN,
    BigInteger,
    Binary,
    Boolean,
    CHAR,
    CLOB,
    DATE,
    DATETIME,
    DECIMAL,
    Date,
    DateTime,
    Enum,
    FLOAT,
    Float,
    INT,
    INTEGER,
    Integer,
    Interval,
    LargeBinary,
    NCHAR,
    NVARCHAR,
    NUMERIC,
    Numeric,
    PickleType,
    SMALLINT,
    SmallInteger,
    String,
    TEXT,
    TIME,
    TIMESTAMP,
    Text,
    Time,
    Unicode,
    UnicodeText,
    VARCHAR,
    )


from sqlalchemy.orm import (
    column_property,
    mapper,
    scoped_session,
    sessionmaker,
    reconstructor,
    relationship,
    backref,
    contains_eager,
    eagerload,
    eagerload_all,
    joinedload,
    synonym
    )

from sqlalchemy.orm.exc import (
    NoResultFound,
    MultipleResultsFound
    )

from sqlalchemy.sql import (
    exists,
    )

from sqlalchemy.sql.expression import (
    asc,
    desc,
    )

from sqlalchemy import func

import re
from pybald.db import engine, dump_engine
from pybald.util import camel_to_underscore, pluralize

# for green operation
import project
from project import mc

from sqlalchemy.orm.interfaces import SessionExtension

class SessionCachingExtension(SessionExtension):
    def __init__(self):
        self.updates = {}
    def after_flush(self, session, flush_context, *pargs, **kargs):
        for instance in session.dirty:
            if hasattr(instance, "update_cache"):
                key, cached_object = instance.update_cache()
                self.updates[key] = cached_object
        for instance in session.new:
            if hasattr(instance, "update_cache"):
                key, cached_object = instance.update_cache()
                self.updates[key] = cached_object

    def after_commit(self, session, *pargs, **kargs):
        for key, value in self.updates.items():
            mc.set(key, value, 180)
        self.updates = {}


session_args = {}

if project.green:
    from SAGreen import eventlet_greenthread_scope
    session_args['scopefunc'] = eventlet_greenthread_scope

if project.session_caching:
    session_args['extension'] = SessionCachingExtension()

session = scoped_session(sessionmaker(bind=engine, **session_args))


import sqlalchemy.ext.declarative
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base(bind=engine)


class NotFound(NoResultFound):
    '''Generic Not Found Error'''
    pass

class ModelMeta(sqlalchemy.ext.declarative.DeclarativeMeta):
    '''
    MetaClass that sets up some common behaviors for pybald models.
    
    Will assign tablename if not defined based on pluralization rules. Also
    applies project global table arguments
    '''
    def __init__(cls, name, bases, ns):
        try:
            if Model not in bases:
                return
        except NameError:
            return
        # set the tablename, if it's user set, use that, otherwise use a function to create one
        cls.__tablename__ = getattr(cls, "__tablename__" , pluralize( camel_to_underscore(name) ))
        # tableargs adds autoload to create schema reflection
        cls.__table_args__ = getattr(cls, "__table_args__", {})
        if project.schema_reflection:
            # create or update the __table_args__ attribute
            cls.__table_args__['autoload'] = True
        if project.global_table_args:
            cls.__table_args__.update(project.global_table_args)

        super(ModelMeta, cls).__init__(name, bases, ns)


class Model(Base):
    '''Pybald Model class, inherits from SQLAlchemy Declarative Base.'''
    __metaclass__ = ModelMeta

    NotFound = sqlalchemy.orm.exc.NoResultFound
    MultipleFound = sqlalchemy.orm.exc.MultipleResultsFound
    # automatically assign id to the table/class
    id = Column(Integer, nullable=False, primary_key=True)

    def save(self, commit=False):
        '''
        Saves (adds) this instance in the current databse session.

        This does not immediatly persist the data since these operations
        occur within a transaction and the sqlalchemy unit-of-work pattern.
        If something causes a rollback before the session is committed,
        these changes will be lost.

        When commit is `True`, flushes the data to the database immediately.
        This does not commit the transaction, for that use 
        :py:meth:`~pybald.db.models.Model.commit`)
        '''

        session.add(self)

        if commit:
            self.flush()
        return self

    def delete(self, commit=False):
        '''
        Delete this instance from the current database session.

        The object will be deleted from the database at the next commit. If
        you want to immediately delete the object, you should follow this
        operation with a commit to emit the SQL to delete the item from
        the database and commit the transaction.
        '''
        session.delete(self)
        if commit:
            self.flush()
        return self


    def flush(self):
        '''
        Syncs all pending SQL changes (including other pending objects) to the underlying
        data store within the current transaction.

        Flush emits all the relevant SQL to the underlying store, but does **not** commit the
        current transaction or close the current database session.
        '''
        session.flush()
        return self


    def commit(self):
        '''
        Commits the entire database session (including other pending objects).

        This emits all relevant SQL to the databse, commits the current transaction,
        and closes the current session (and database connection) and returns it to the
        connection pool. Any data operations after this will pull a new database
        session from the connection pool.
        '''
        session.commit()
        return self

    @classmethod
    def get(cls, **where):
        '''
        A convenience method that constructs a load query with keyword 
        arguments as the filter arguments and return a single instance.
        '''
        return cls.load(**where).one()

    @classmethod
    def all(cls, **where):
        '''
        Returns a collection of objects that can be filtered for 
        specific collections.

        all() without arguments returns all the items of the model type.
        '''
        return cls.load(**where).all()

    # methods that return queries (must execute to retrieve)
    # =============================================================
    @classmethod
    def load(cls, **where):
        '''
        Convenience method to build a sqlalchemy query to return stored
        objects.

        Returns a query object. This query object must be executed to retrieve
        actual items from the database.
        '''
        if where:
            return session.query(cls).filter_by(**where)
        else:
            return session.query(cls)

    @classmethod
    def filter(cls, *pargs, **kargs):
        '''
        Convenience method that auto-builds the query and passes the filter
        to it.

        Returns a query object.
        '''
        return session.query(cls).filter(*pargs, **kargs)


    @classmethod
    def query(cls):
        '''
        Convenience method to return a query based on the current object
        class.
        '''
        return session.query(cls)

    @classmethod
    def show_create_table(cls):
        '''
        Uses the simple dump_engine to print to stdout the SQL for this
        table.
        '''
        cls.__table__.create(dump_engine)

