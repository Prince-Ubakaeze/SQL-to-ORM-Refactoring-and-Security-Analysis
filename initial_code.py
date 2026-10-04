import logging
from typing import List, Optional
from sqlalchemy import String, create_engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# Configure logging for production visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. Database Setup & Declarative Base Configuration
# ==============================================================================


class Base(DeclarativeBase):
    """Base class for all ORM models using SQLAlchemy 2.0 style declarative mapping."""

    pass


# ==============================================================================
# 2. ORM Model Definition
# ==============================================================================


class User(Base):
    """Declarative ORM Model representing the 'users' table."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


# ==============================================================================
# 3. Data Access / CRUD Service Layer
# ==============================================================================


class UserService:
    """Service layer managing database sessions, input validation, and CRUD operations."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def _validate_input(self, username: str, email: Optional[str] = None) -> None:
        """Basic validation to ensure inputs are non-empty and well-formed."""
        if not username or not username.strip():
            raise ValueError("Username cannot be empty.")
        if email is not None:
            if not email or "@" not in email or "." not in email:
                raise ValueError(f"Invalid email address provided: '{email}'")

    def create_user(self, username: str, email: str) -> Optional[User]:
        """Creates and persists a new user record in a managed transaction."""
        self._validate_input(username, email)

        with self.session_factory() as session:
            try:
                user = User(username=username.strip(), email=email.strip())
                session.add(user)
                session.commit()
                # Refresh populates server-generated fields like primary key (id)
                session.refresh(user)
                logger.info(f"User created successfully: {user}")
                return user
            except IntegrityError as e:
                session.rollback()
                logger.error(
                    f"Integrity error creating user '{username}': Constraint violation."
                )
                raise ValueError(
                    "A user with that username or email already exists."
                ) from e
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error during user creation: {e}")
                raise

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by exact username match."""
        self._validate_input(username)

        with self.session_factory() as session:
            try:
                stmt = select(User).where(User.username == username.strip())
                return session.scalars(stmt).first()
            except SQLAlchemyError as e:
                logger.error(f"Error retrieving user '{username}': {e}")
                raise

    def update_user_email(self, username: str, new_email: str) -> Optional[User]:
        """Updates an existing user's email within a managed transaction."""
        self._validate_input(username, new_email)

        with self.session_factory() as session:
            try:
                stmt = select(User).where(User.username == username.strip())
                user = session.scalars(stmt).first()

                if not user:
                    logger.warning(
                        f"Update failed: User '{username}' does not exist."
                    )
                    return None

                user.email = new_email.strip()
                session.commit()
                session.refresh(user)
                logger.info(f"Updated email for user '{username}' to '{new_email}'.")
                return user
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Integrity error updating email for '{username}': {e}")
                raise ValueError(
                    "The specified email is already in use by another account."
                ) from e
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error during email update: {e}")
                raise

    def delete_user(self, username: str) -> bool:
        """Deletes a user record by username within a managed transaction."""
        self._validate_input(username)

        with self.session_factory() as session:
            try:
                stmt = select(User).where(User.username == username.strip())
                user = session.scalars(stmt).first()

                if not user:
                    logger.warning(
                        f"Delete failed: User '{username}' does not exist."
                    )
                    return False

                session.delete(user)
                session.commit()
                logger.info(f"User '{username}' deleted successfully.")
                return True
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error during user deletion: {e}")
                raise

    def list_all_users(self) -> List[User]:
        """Retrieves all user records ordered by ID."""
        with self.session_factory() as session:
            try:
                stmt = select(User).order_by(User.id)
                return list(session.scalars(stmt).all())
            except SQLAlchemyError as e:
                logger.error(f"Database error fetching user list: {e}")
                raise


# ==============================================================================
# 4. Demonstration / Execution Script
# ==============================================================================

if __name__ == "__main__":
    # Database Connection Configuration
    # Note: Using SQLite in-memory database for immediate local execution.
    # To connect to MySQL/MariaDB, replace the string with PyMySQL driver syntax:
    # DATABASE_URL = "mysql+pymysql://db_user:db_password@localhost:3306/my_database"
    DATABASE_URL = "sqlite:///:memory:"

    logger.info("Initializing Database Engine...")
    engine = create_engine(DATABASE_URL, echo=False)

    # 1. Create tables using model metadata
    logger.info("Creating database tables based on ORM Metadata...")
    Base.metadata.create_all(bind=engine)

    # 2. Configure session factory
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    user_service = UserService(session_factory=SessionFactory)

    # --- DEMONSTRATION OF CRUD OPERATIONS ---

    print("\n--- 1. Creating Users ---")
    alice = user_service.create_user("alice_dev", "alice@example.com")
    bob = user_service.create_user("bob_designer", "bob@example.com")
    print(f"Created: {alice}")
    print(f"Created: {bob}")

    print("\n--- 2. Retrieving User ---")
    found_user = user_service.get_user_by_username("alice_dev")
    print(f"Retrieved user by username: {found_user}")

    print("\n--- 3. Listing All Users ---")
    all_users = user_service.list_all_users()
    for u in all_users:
        print(f" - {u}")

    print("\n--- 4. Updating User Email ---")
    updated_user = user_service.update_user_email(
        "alice_dev", "alice.new@example.com"
    )
    print(f"Updated user: {updated_user}")

    print("\n--- 5. Handling Validation & Constraints ---")
    try:
        # Duplicate username attempt
        user_service.create_user("alice_dev", "different@example.com")
    except ValueError as err:
        print(f"Caught expected error: {err}")

    try:
        # Invalid email input
        user_service.create_user("charlie", "invalid-email-format")
    except ValueError as err:
        print(f"Caught expected validation error: {err}")

    print("\n--- 6. Deleting User ---")
    was_deleted = user_service.delete_user("bob_designer")
    print(f"Deletion status for 'bob_designer': {was_deleted}")

    print("\n--- 7. Final User List ---")
    for u in user_service.list_all_users():
        print(f" - {u}")

    logger.info("Demonstration complete.")