"""
Database connection and session management.

This module provides database connectivity, session management, and
connection pooling for the browser automation framework.
"""

import asyncio
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine

from core.exceptions import ConfigurationError, DatabaseError
from .models import Base


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False
    ):
        """Initialize database manager.
        
        Args:
            database_url: Database connection URL
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum number of connections to create beyond pool_size
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Time to recycle connections (seconds)
            echo: Whether to echo SQL statements
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        
        self._engine: Optional[Engine] = None
        self._async_engine: Optional[Any] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[async_sessionmaker] = None
    
    def initialize(self) -> None:
        """Initialize database connections and session factories."""
        try:
            # Create synchronous engine
            self._engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                echo=self.echo
            )
            
            # Create async engine (convert postgresql:// to postgresql+asyncpg://)
            async_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://")
            self._async_engine = create_async_engine(
                async_url,
                poolclass=QueuePool,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                echo=self.echo
            )
            
            # Create session factories
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False
            )
            
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False
            )
            
            # Add connection event listeners
            self._setup_event_listeners()
            
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise ConfigurationError(f"Database initialization failed: {e}")
    
    def _setup_event_listeners(self) -> None:
        """Setup database event listeners for monitoring and optimization."""
        
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance (if using SQLite)."""
            if "sqlite" in self.database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
        
        @event.listens_for(self._engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout."""
            logger.debug("Database connection checked out")
        
        @event.listens_for(self._engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin."""
            logger.debug("Database connection checked in")
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        if not self._async_engine:
            raise DatabaseError("Database not initialized")
        
        try:
            async with self._async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise DatabaseError(f"Table creation failed: {e}")
    
    async def drop_tables(self) -> None:
        """Drop all database tables."""
        if not self._async_engine:
            raise DatabaseError("Database not initialized")
        
        try:
            async with self._async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise DatabaseError(f"Table drop failed: {e}")
    
    def get_session(self) -> Session:
        """Get a synchronous database session."""
        if not self._session_factory:
            raise DatabaseError("Database not initialized")
        
        return self._session_factory()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an asynchronous database session."""
        if not self._async_session_factory:
            raise DatabaseError("Database not initialized")
        
        async with self._async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """Perform database health check."""
        try:
            async with self.get_async_session() as session:
                result = await session.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information."""
        if not self._engine:
            return {"status": "not_initialized"}
        
        pool = self._engine.pool
        
        return {
            "status": "connected",
            "database_url": self.database_url.split("@")[-1],  # Hide credentials
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }
    
    async def close(self) -> None:
        """Close database connections."""
        try:
            if self._async_engine:
                await self._async_engine.dispose()
            
            if self._engine:
                self._engine.dispose()
            
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def initialize_database(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    echo: bool = False
) -> DatabaseManager:
    """Initialize the global database manager."""
    global db_manager
    
    db_manager = DatabaseManager(
        database_url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        echo=echo
    )
    
    db_manager.initialize()
    return db_manager


def get_database_manager() -> DatabaseManager:
    """Get the global database manager."""
    if db_manager is None:
        raise DatabaseError("Database not initialized. Call initialize_database() first.")
    
    return db_manager


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session (convenience function)."""
    manager = get_database_manager()
    async with manager.get_async_session() as session:
        yield session


class DatabaseError(Exception):
    """Database-related error."""
    pass
