"""
Database Connection Management

Provides async PostgreSQL connection pooling and session management
for the CMMC Compliance Platform API.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from asyncpg.pool import Pool

logger = logging.getLogger(__name__)


class Database:
    """
    Database connection manager with connection pooling

    Manages async PostgreSQL connections using asyncpg for optimal performance.
    """

    def __init__(self):
        self.pool: Pool | None = None
        self._database_url: str | None = None

    def get_database_url(self) -> str:
        """
        Get database URL from environment variables

        Returns:
            str: PostgreSQL connection URL

        Raises:
            ValueError: If DATABASE_URL is not set
        """
        if self._database_url:
            return self._database_url

        # Try environment variable first
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            # Build from individual components
            db_user = os.getenv("DB_USER", "cmmc_user")
            db_password = os.getenv("DB_PASSWORD", "cmmc_password")
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "cmmc_db")

            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        self._database_url = database_url
        return database_url

    async def connect(self) -> None:
        """
        Create database connection pool

        Establishes a connection pool with optimal settings for
        concurrent async operations.
        """
        if self.pool is not None:
            logger.warning("Database pool already exists")
            return

        database_url = self.get_database_url()

        try:
            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=5,              # Minimum connections in pool
                max_size=20,             # Maximum connections in pool
                max_queries=50000,       # Max queries per connection before recycling
                max_inactive_connection_lifetime=300.0,  # 5 minutes
                timeout=30.0,            # Connection timeout
                command_timeout=60.0,    # Query timeout
            )

            # Verify connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to database: {version}")

            logger.info("Database connection pool created successfully")

        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def disconnect(self) -> None:
        """
        Close database connection pool

        Gracefully closes all connections in the pool.
        """
        if self.pool is None:
            logger.warning("Database pool does not exist")
            return

        try:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
            raise

    def get_pool(self) -> Pool:
        """
        Get database connection pool

        Returns:
            Pool: asyncpg connection pool

        Raises:
            RuntimeError: If pool is not initialized
        """
        if self.pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call database.connect() first."
            )
        return self.pool

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Acquire a connection from the pool

        Context manager that acquires a connection from the pool
        and automatically releases it when done.

        Usage:
            async with database.acquire() as conn:
                result = await conn.fetch("SELECT * FROM users")

        Yields:
            Connection: Database connection
        """
        pool = self.get_pool()
        async with pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args) -> str:
        """
        Execute a query that doesn't return rows

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            str: Status message (e.g., "INSERT 0 1")
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """
        Fetch multiple rows

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            list: List of records
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """
        Fetch single row

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Record or None
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """
        Fetch single value

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Any: Single value or None
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def health_check(self) -> dict:
        """
        Check database health

        Returns:
            dict: Health check results
        """
        try:
            pool = self.get_pool()

            # Check pool status
            pool_size = pool.get_size()
            pool_free = pool.get_idle_size()

            # Execute simple query
            async with self.acquire() as conn:
                result = await conn.fetchval("SELECT 1")

            return {
                "status": "healthy" if result == 1 else "degraded",
                "pool_size": pool_size,
                "pool_free": pool_free,
                "pool_in_use": pool_size - pool_free,
                "max_size": pool.get_max_size(),
                "min_size": pool.get_min_size()
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global database instance
database = Database()


async def get_database() -> Database:
    """
    Dependency for FastAPI endpoints

    Usage:
        @app.get("/users")
        async def get_users(db: Database = Depends(get_database)):
            users = await db.fetch("SELECT * FROM users")
            return users

    Returns:
        Database: Database instance
    """
    return database


async def get_db_pool() -> Pool:
    """
    Dependency for getting connection pool

    Usage:
        @app.get("/users")
        async def get_users(pool: Pool = Depends(get_db_pool)):
            async with pool.acquire() as conn:
                users = await conn.fetch("SELECT * FROM users")
            return users

    Returns:
        Pool: Connection pool
    """
    return database.get_pool()


# Lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan context manager

    Handles database connection on startup and shutdown.

    Usage in main.py:
        from database import lifespan

        app = FastAPI(lifespan=lifespan)
    """
    # Startup
    logger.info("Starting up - connecting to database...")
    await database.connect()
    yield
    # Shutdown
    logger.info("Shutting down - disconnecting from database...")
    await database.disconnect()
