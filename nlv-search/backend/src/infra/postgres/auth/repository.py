from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.infra.postgres.auth.models import User


class UserRepository:
    """PostgreSQL repository for user CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an active SQLAlchemy async session."""

        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch a user by primary key.

        Args:
            user_id: UUID string.

        Returns:
            User instance or None if not found.
        """

        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Fetch a user by username.

        Args:
            username: Unique username string.

        Returns:
            User instance or None if not found.
        """

        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address.

        Args:
            email: Email address string.

        Returns:
            User instance or None if not found.
        """

        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, username: str, email: str, password_hash: str) -> User:
        """Insert a new user and flush to obtain the generated ID.

        Args:
            username: Unique username.
            email: Unique email address.
            password_hash: Bcrypt password hash.

        Returns:
            Newly created and refreshed User instance.
        """

        user = User(username=username, email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user: User) -> None:
        """Delete a user and flush the session.

        Args:
            user: User instance to delete.
        """

        await self.session.delete(user)
        await self.session.flush()
