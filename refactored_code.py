import logging
import os
import re
from typing import List, Optional
from sqlalchemy import String, create_engine, select
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. ORM Base and Model Definition (Declarative Mapping)
# ==============================================================================

class Base(DeclarativeBase):
    """Base class for declarative ORM models in SQLAlchemy 2.x."""
    pass


class User(Base):
    """
    ORM Model mapped to the 'users' table.
    
    Demonstrates SQLAlchemy 2.0 type-annotated mapping with Mapped[] and mapped_column().
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        nullable=False, 
        index=True
    )
    email: Mapped[str] = mapped_column(
        String(120), 
        unique=True, 
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


# ==============================================================================
# 2. Service Layer for CRUD Operations & Business Logic
# ==============================================================================

class UserService:
    """
    Encapsulates CRUD operations and business logic for the User model.
    Handles explicit session context management, transactions, and validation.
    """

    EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    @classmethod
    def _validate_user_data(cls, username: str, email: Optional[str] = None) -> None:
        """Validates input before querying or persisting changes."""
        if not username or not username.strip():
            raise ValueError("Username cannot be empty or whitespace.")
        
        if email is not None:
            if not email or not email.strip():
                raise ValueError("Email cannot be empty or whitespace.")
            if not cls.EMAIL_REGEX.match(email.strip()):
                raise ValueError(f"Invalid email format: '{email}'")

    def create_user(self, username: str, email: str) -> User:
        """Creates and persists a new user record in a transaction."""
        self._validate_user_data(username, email)
        clean_username = username.strip()
        clean_email = email.strip()

        with self.session_factory() as session:
            try:
                user = User(username=clean_username, email=clean_email)
                session.add(user)
                session.commit()
                # Refresh populates server-generated fields like primary key (id)
                session.refresh(user)
                logger.info("Successfully created user: %s", user)
                return user
            except IntegrityError as e:
                session.rollback()
                logger.error("Integrity error creating user '%s': Unique constraint violation.", clean_username)
                raise ValueError(f"User with username '{clean_username}' or email '{clean_email}' already exists.") from e
            except SQLAlchemyError as e:
                session.rollback()
                logger.error("Database error occurred while creating user '%s': %s", clean_username, e)
                raise

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by exact username match using parameterized ORM selection."""
        self._validate_user_data(username)
        clean_username = username.strip()

        with self.session_factory() as session:
            try:
                # Bound parameter generated automatically via SQLAlchemy ORM expression
                stmt = select(User).where(User.username == clean_username)
                user = session.scalars(stmt).first()
                if user:
                    logger.info("Found user: %s", user)
                else:
                    logger.info("No user found with username: '%s'", clean_username)
                return user
            except SQLAlchemyError as e:
                logger.error("Error retrieving user '%s': %s", clean_username, e)
                raise

    def update_user_email(self, username: str, new_email: str) -> Optional[User]:
        """Updates an existing user's email within an explicit transaction."""
        self._validate_user_data(username, new_email)
        clean_username = username.strip()
        clean_email = new_email.strip()

        with self.session_factory() as session:
            try:
                stmt = select(User).where(User.username == clean_username)
                user = session.scalars(stmt).first()

                if not user:
                    logger.warning("Update failed: User '%s' does not exist.", clean_username)
                    return None

                user.email = clean_email
                session.commit()
                session.refresh(user)
                logger.info("Updated email for user '%s' to '%s'", clean_username, clean_email)
                return user
            except IntegrityError as e:
                session.rollback()
                logger.error("Integrity constraint error updating email for user '%s': %s", clean_username, e)
                raise ValueError(f"The email address '{clean_email}' is already in use by another account.") from e
            except SQLAlchemyError as e:
                session.rollback()
                logger.error("Database error while updating email for '%s': %s", clean_username, e)
                raise

    def delete_user(self, username: str) -> bool:
        """Deletes a user by username in an explicit transaction."""
        self._validate_user_data(username)
        clean_username = username.strip()

        with self.session_factory() as session:
            try:
                stmt = select(User).where(User.username == clean_username)
                user = session.scalars(stmt).first()

                if not user:
                    logger.warning("Delete failed: User '%s' does not exist.", clean_username)
                    return False

                session.delete(user)
                session.commit()
                logger.info("Successfully deleted user '%s'", clean_username)
                return True
            except SQLAlchemyError as e:
                session.rollback()
                logger.error("Database error while deleting user '%s': %s", clean_username, e)
                raise

    def list_all_users(self) -> List[User]:
        """Retrieves all user records ordered by primary key."""
        with self.session_factory() as session:
            try:
                stmt = select(User).order_by(User.id)
                users = list(session.scalars(stmt).all())
                logger.info("Retrieved %d user(s).", len(users))
                return users
            except SQLAlchemyError as e:
                logger.error("Database error while listing users: %s", e)
                raise


# ==============================================================================
# 3. Application Entrypoint & Demonstration
# ==============================================================================

if __name__ == "__main__":
    # Retrieve connection string from environment variable.
    # Fall back to SQLite in-memory for demonstration if environment variable is not set.
    # Production connection URL format (PyMySQL driver):
    #   mysql+pymysql://<user>:<password>@<host>:<port>/<database_name>
    DEFAULT_DEMO_URL = "sqlite:///:memory:"
    database_url = os.getenv("DATABASE_URL", DEFAULT_DEMO_URL)

    if database_url == DEFAULT_DEMO_URL:
        logger.warning(
            "DATABASE_URL not found in environment. Using in-memory SQLite fallback for demonstration."
        )
    else:
        logger.info("Configured database connection from environment variable.")

    # Initialize Engine and Session Factory
    engine = create_engine(database_url, echo=False, pool_pre_ping=True)

    try:
        # Create missing database tables using metadata
        logger.info("Creating missing database tables via Base.metadata.create_all()...")
        Base.metadata.create_all(bind=engine)
    except DBAPIError as e:
        logger.critical(
            "Failed to connect to target database or build schema. "
            "Ensure the target database server and schema exist. Error: %s", e
        )
        raise SystemExit(1)

    # Configure Thread-Local / Scoped Session Factory
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
    user_service = UserService(session_factory=SessionFactory)

    # --------------------------------------------------------------------------
    # Executable CRUD Demonstration
    # --------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STARTING ORM CRUD DEMONSTRATION")
    print("=" * 60)

    # 1. Create Users
    print("\n--- 1. Creating Users ---")
    user_1 = user_service.create_user("alice_dev", "alice@example.com")
    user_2 = user_service.create_user("bob_designer", "bob@example.com")
    print(f"Created: {user_1}")
    print(f"Created: {user_2}")

    # 2. Retrieve User by Username
    print("\n--- 2. Retrieving User by Username ---")
    retrieved = user_service.get_user_by_username("alice_dev")
    print(f"QueryResult: {retrieved}")

    # 3. List All Users
    print("\n--- 3. Listing All Users ---")
    for u in user_service.list_all_users():
        print(f" - {u}")

    # 4. Update User Email
    print("\n--- 4. Updating User Email ---")
    updated = user_service.update_user_email("alice_dev", "alice.newdomain@example.com")
    print(f"Updated User: {updated}")

    # 5. Validation & Constraint Exception Handling
    print("\n--- 5. Input Validation & Integrity Error Demonstrations ---")
    try:
        # Duplicate username violation
        user_service.create_user("alice_dev", "conflict@example.com")
    except ValueError as err:
        print(f"Caught expected constraint error: {err}")

    try:
        # Malformed email validation
        user_service.create_user("charlie", "not-a-valid-email")
    except ValueError as err:
        print(f"Caught expected validation error: {err}")

    # 6. Delete User
    print("\n--- 6. Deleting User ---")
    deleted_status = user_service.delete_user("bob_designer")
    print(f"Deletion status for 'bob_designer': {deleted_status}")

    # 7. Final State Audit
    print("\n--- 7. Final Database State ---")
    final_users = user_service.list_all_users()
    for u in final_users:
        print(f" - {u}")

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)