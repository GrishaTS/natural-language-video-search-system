from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from src.core import security
from src.infra.postgres.auth import User, UserRepository


class AuthService:
    """Application service for user registration, authentication, and deletion."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an active database session."""

        self.session = session
        self.repo = UserRepository(session)

    async def register_user(self, username: str, email: str, password: str) -> User:
        """Register a new user with a hashed password.

        Args:
            username: Desired unique username.
            email: Unique email address.
            password: Plain-text password to hash with bcrypt.

        Returns:
            Newly created User instance.

        Raises:
            ValueError: If the username or email is already taken.
        """

        existing_user = await self.repo.get_by_username(username)

        if existing_user:
            logger.info(f"Register: username '{username}' already taken")
            raise ValueError("Username already taken")

        existing_email = await self.repo.get_by_email(email)

        if existing_email:
            logger.info(f"Register: email '{email}' already used")
            raise ValueError("Email already used")

        password_hash = security.get_password_hash(password)
        user = await self.repo.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
        )
        await self.session.commit()
        logger.info(f"Register: user '{user.username}' created")
        return user

    async def authenticate_user(self, username: str, password: str) -> User | None:
        """Verify username and password; return the user if valid, None otherwise.

        Args:
            username: Username to look up.
            password: Plain-text password to verify.

        Returns:
            User instance on success, None on bad credentials or inactive account.
        """

        user = await self.repo.get_by_username(username)

        if not user:
            return None

        if not user.is_active:
            return None

        if not security.verify_password(password, user.password_hash):
            return None

        return user

    async def delete_user(self, user: User) -> None:
        """Delete a user record and commit the transaction.

        Args:
            user: User instance to delete.
        """

        await self.repo.delete_user(user)
        await self.session.commit()
        logger.info(f"User '{user.username}' deleted")

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Fetch a user by UUID.

        Args:
            user_id: UUID string.

        Returns:
            User instance or None if not found.
        """

        return await self.repo.get_by_id(user_id)
