# SQL to ORM Refactoring and Security Analysis

## Overview

This assignment refactors a procedural Python database application that uses `mysql.connector`, a database cursor, and SQL statements into a structured implementation using the SQLAlchemy Object-Relational Mapper (ORM).

The refactored application defines a declarative `User` model mapped to a `users` table. It creates missing tables from the model metadata, opens an ORM `Session`, and implements create, retrieve, update, delete, and list operations.

## Files

- `initial_code.py` contains the original procedural example. Its insert operation uses parameter binding through the MySQL connector.
- `refactored_code.py` contains the SQLAlchemy declarative model, engine and session setup, table creation, CRUD operations, validation, exception handling, and transaction management.
- `README.md` documents the refactoring, security considerations, and maintainability benefits.

## Setup and Usage

Install the required dependencies:

```text
pip install SQLAlchemy mysql-connector-python
```

Set a connection URL before running the refactored program. Use your own credentials and do not commit them to the repository:

```text
DATABASE_URL=mysql+mysqlconnector://username:password@localhost/example_db
```

Run the program from this folder:

```text
python refactored_code.py
```

The program creates missing tables, adds a sample user, queries that user, updates the email, and lists the users.

## Security Improvements

The ORM expressions use bound parameters rather than concatenating user input into SQL strings. This reduces the SQL injection risk associated with unsafe string construction. The `User` model also centralizes required fields and uniqueness constraints, while failed writes roll back the active session.

An ORM is not a complete security guarantee. Unsafe textual SQL, weak database credentials, poor input validation, or exposed secrets can still create vulnerabilities. Secure coding practices remain necessary whenever raw SQL or external input is introduced.

The original example already uses a parameterized insert, which is safer than formatting user input directly into SQL. The ORM version improves the overall structure by applying the same parameterized behavior through reusable model expressions.

## Maintainability Improvements

The `User` class gives the application one clear representation of the `users` table. CRUD functions receive a `Session`, which makes transaction boundaries visible and allows tests to use a controlled database session.

The model and reusable ORM expressions reduce duplicated SQL, improve readability, and make future schema or database changes easier to manage. The object-centered design also reduces errors caused by repeating table names, column names, placeholders, and SQL syntax throughout the application.

`Base.metadata.create_all(engine)` creates missing tables represented by the models. It does not create the MySQL database itself and is not a replacement for a migration system in a production application.

## Technologies

- Python
- SQLAlchemy
- MySQL
- MySQL Connector/Python

## Repository Structure

```text
Artificial-Intelligence-in-Software-Engineering/
└── SQL to ORM Refactoring and Security Analysis/
    ├── initial_code.py
    ├── refactored_code.py
    └── README.md
```

## Conclusion

The refactoring demonstrates how SQLAlchemy can transform procedural database code into a more structured, readable, testable, maintainable, and secure object-oriented application while preserving responsible database practices.
