"""Define SQLAlchemy persistence models for Memoria base.

This module describes storage shape and indexes; lifecycle rules remain in domain services.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
