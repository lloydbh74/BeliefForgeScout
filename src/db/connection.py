"""
Database connection management for Social Reply Bot.

Provides SQLAlchemy session management, connection pooling, and helper functions.
"""

from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from src.db.models import Base
from src.config.loader import get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL (default: from config)
        """
        if database_url is None:
            _, env_config = get_config()
            database_url = env_config.database_url

        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize database engine and session factory.
        Should be called once at application startup.
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return

        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                self.database_url,
                poolclass=pool.QueuePool,
                pool_size=5,  # Default pool size
                max_overflow=10,  # Max overflow connections
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=False  # Set to True for SQL query logging
            )

            # Configure session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Add connection event listeners
            self._setup_event_listeners()

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self._initialized = True
            logger.info("Database initialized successfully")

        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for debugging and monitoring"""

        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Called when a new database connection is created"""
            logger.debug("New database connection established")

        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Called when a connection is retrieved from the pool"""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Called when a connection is returned to the pool"""
            logger.debug("Connection returned to pool")

    def create_tables(self) -> None:
        """
        Create all tables defined in models.
        Should only be called for testing or if init-db.sql didn't run.
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def drop_tables(self) -> None:
        """
        Drop all tables. USE WITH CAUTION.
        Only for testing/development.
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.warning("Dropping all database tables")
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy session

        Example:
            session = db_manager.get_session()
            try:
                # Use session
                session.commit()
            except Exception as e:
                session.rollback()
                raise
            finally:
                session.close()
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.

        Yields:
            SQLAlchemy session

        Example:
            with db_manager.session_scope() as session:
                session.add(obj)
                # Commit happens automatically on success
                # Rollback happens automatically on exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close database engine and all connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance (singleton pattern).

    Returns:
        DatabaseManager instance
    """
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()

    return _db_manager


def get_db_session() -> Session:
    """
    Get a new database session from global manager.

    Returns:
        SQLAlchemy session

    Example:
        session = get_db_session()
        try:
            # Use session
            session.commit()
        finally:
            session.close()
    """
    return get_db_manager().get_session()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup (context manager).

    Yields:
        SQLAlchemy session

    Example:
        with get_db() as session:
            result = session.query(ReplyQueue).filter_by(status='pending').all()
    """
    db_manager = get_db_manager()
    with db_manager.session_scope() as session:
        yield session


# FastAPI dependency injection helper
def get_db_dependency() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Example:
        @app.get("/replies")
        def get_replies(db: Session = Depends(get_db_dependency)):
            return db.query(ReplyQueue).all()
    """
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


if __name__ == "__main__":
    # Test database connection
    import sys

    logging.basicConfig(level=logging.INFO)

    try:
        db_manager = get_db_manager()
        logger.info("✓ Database connection successful")

        # Test session
        with db_manager.session_scope() as session:
            result = session.execute("SELECT NOW()").scalar()
            logger.info(f"✓ Database time: {result}")

        logger.info("✓ All database tests passed")

    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        sys.exit(1)
    finally:
        if _db_manager:
            _db_manager.close()
