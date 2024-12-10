import logging
from typing import List
from flask import jsonify
import sqlite3
import os
import hashlib
from utils.logger import configure_logger

import requests
from models.book_model import Book
from utils.openlibrary import session

logger = logging.getLogger(__name__)
configure_logger(logger)
DB_PATH = "/app/db/library.db"


class User:
    id: int
    username: str
    password: str
    salt: str
    personal_library = []  # list of JSON blobs/python dictionary
    favorite_books = []  # list of JSON blobs/python dictionaries
    reviews = []  # list of JSON blobs/python dictionaries

    def __init__(self, id: int = None, username: str = None):
        self.id = id
        self.username = username
        self.salt = None
        self.password_hash = None

    def set_password(self, password: str) -> None:
        """Hash the password with a random salt using SHA-512
        Args:
            password: The plain text password to hash
        """
        self.salt = os.urandom(64).hex()
        self.password_hash = hashlib.sha512(
            f"{password}{self.salt}".encode()
        ).hexdigest()

    def check_password(self, password: str) -> bool:
        """Verify the password against stored hash using SHA-512
        Args:
            password: The plain text password to verify
        Returns:
            bool: True if password matches, False otherwise
        """
        if not self.salt or not self.password_hash:
            return False
        password_to_check = hashlib.sha512(
            f"{password}{self.salt}".encode()
        ).hexdigest()
        return self.password_hash == password_to_check

    @staticmethod
    def create_user_account(username: str, password: str):
        """Create a new user account with hashed password
        Args:
            username: The username for the new account
            password: The plain text password to hash
        Returns:
            tuple: (message dict, status code)
        """
        try:
            # Create new user instance and set password
            user = User(username=username)
            user.set_password(password)

            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (username, password, salt)
                    VALUES (?, ?, ?)
                """,
                    (user.username, user.password_hash, user.salt),
                )
                conn.commit()
                user.id = cursor.lastrowid

            logger.info("User successfully added to the database: %s", username)
            return (
                jsonify({"message": f"Account created successfully for {username}"}),
                200,
            )

        except sqlite3.IntegrityError:
            logger.error("Duplicate user: %s", username)
            return (
                jsonify({"message": f"User with username '{username}' already exists"}),
                400,
            )
        except sqlite3.Error as e:
            logger.error("Database error: %s", str(e))
            return jsonify({"message": "Error creating account"}), 500

    @staticmethod
    def get_user_by_username(username: str) -> "User":
        """Retrieve a user from the database by username
        Args:
            username: The username to look up
        Returns:
            User: User instance if found, None otherwise
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, username, password, salt
                    FROM users
                    WHERE username = ?
                """,
                    (username,),
                )
                user_data = cursor.fetchone()

                if user_data:
                    user = User(id=user_data[0], username=user_data[1])
                    user.password_hash = user_data[2]
                    user.salt = user_data[3]
                    return user
                return None

        except sqlite3.Error as e:
            logger.error("Database error: %s", str(e))
            return None

    def update_password(self, new_password: str):
        """Update the user's password with new hash and salt
        Args:
            new_password: The new plain text password
        Returns:
            tuple: (message dict, status code)
        """
        try:
            self.set_password(new_password)

            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE users
                    SET password = ?, salt = ?
                    WHERE id = ?
                """,
                    (self.password_hash, self.salt, self.id),
                )
                conn.commit()

            return jsonify({"message": "Password updated successfully"}), 200

        except sqlite3.Error as e:
            logger.error("Database error updating password: %s", str(e))
            return jsonify({"message": "Error updating password"}), 500


def get_library(user):
    """Get all books in the user's library organized by status and favorites
    Arguments:
    user: class User
    Returns:
    tuple: (jsonified response, status_code)
    """
    library = {
        "books": {},
        "favorites": [book.to_dict() for book in user.favorite_books],
    }

    # Organize books by status
    for book in user.personal_library:
        if book.status not in library["books"]:
            library["books"][book.status] = []
        library["books"][book.status].append(book.to_dict())

    return jsonify(library), 200


def add_book_personal_library(user, book_data):
    """Add a book to the user's personal library using OpenLibrary API
    Arguments:
    user: class User
    book_data: dict containing book information (must include 'title', optional 'author')
    Returns:
    tuple: (jsonified response, status_code)
    """
    if not book_data.get("title"):
        return {"message": "Please provide a book title"}, 400

    # Set up OpenLibrary API search parameters
    params = {
        "title": book_data["title"],
        "fields": "title,author_name,isbn",
        "limit": 5,
    }

    if "author" in book_data:
        params["author"] = book_data["author"]

    # Search OpenLibrary API
    try:
        response = session.get(
            "https://openlibrary.org/search.json",
            params=params,
        )
        response.raise_for_status()
    except requests.RequestException:
        return {"message": "Failed to fetch from OpenLibrary"}, 500

    books = response.json().get("docs", [])

    if not books:
        return {"message": "No books found with that title"}, 404

    if len(books) == 1 or "author" in book_data:
        # Add first matching book
        book = books[0]

        # Check for duplicate books
        for existing_book in user.personal_library:
            if (
                existing_book.title.lower() == book.get("title", "Unknown").lower()
                and existing_book.author.lower()
                == book.get("author_name", ["Unknown"])[0].lower()
            ):
                return {
                    "message": f"'{book.get('title', 'Unknown')}' by {book.get('author_name', ['Unknown'])[0]} is already in your library with status: '{existing_book.status}'",
                    "book": existing_book.to_dict(),
                }, 400

        # If no duplicate found, add the new book
        new_book = Book(
            id=len(user.personal_library) + 1,
            title=book.get("title", "Unknown"),
            author=book.get("author_name", ["Unknown"])[0],
            isbn=book.get("isbn", [None])[0] if book.get("isbn") else None,
            status="Want to Read",
        )
        user.personal_library.append(new_book)

        return {
            "message": f"Success! '{new_book.title}' by {new_book.author} has been added to your library.",
            "book": new_book.to_dict(),
        }, 200

    # Multiple books found
    return {
        "message": f"I found {len(books)} books with that title. Please specify the author's name to help me find the right one:",
        "books": [
            {
                "id": None,
                "title": book.get("title", "Unknown"),
                "author": book.get("author_name", ["Unknown"])[0],
                "isbn": book.get("isbn", [None])[0] if book.get("isbn") else None,
            }
            for book in books
        ],
    }, 300


def add_book_favorite_books(user, book_id: int):
    """Add a book from personal library to favorite books
    Arguments:
    user: class User
    book_id: int, ID of the book to add to favorites
    Returns:
    tuple: (jsonified response, status_code)
    """
    # Find the book in personal library
    book_to_favorite = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_favorite = book
            break

    if not book_to_favorite:
        return (
            jsonify(
                {
                    "message": f"Book with ID {book_id} not found in your personal library"
                }
            ),
            404,
        )

    # Check if book is already in favorites
    for book in user.favorite_books:
        if book.id == book_id:
            return (
                jsonify({"message": f"'{book.title}' is already in your favorites"}),
                400,
            )

    # Update book status to "Read"
    book_to_favorite.status = "Read"

    # Add to favorites
    user.favorite_books.append(book_to_favorite)

    return (
        jsonify(
            {
                "message": f"'{book_to_favorite.title}' has been added to your favorites and marked as Read",
                "book": book_to_favorite.to_dict(),
            }
        ),
        200,
    )


def add_review(user, review, book_id):
    """Adding a user's review of a particular book
    Arguments:
    user: class User
    review: string, review to be added
    book_id: int, ID of the book to review
    Returns:
    tuple: (jsonified response, status_code)
    """

    if not review:
        return jsonify({"message": "Please provide a review"}), 400

    # Find the book in personal library
    book_to_review = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_review = book
            break

    if not book_to_review:
        return (
            jsonify(
                {
                    "message": f"Book with ID {book_id} not found in your personal library"
                }
            ),
            404,
        )

    # Check if user has already reviewed the book
    for review in user.reviews:
        if review.id == book_id:
            return (
                jsonify(
                    {"message": f"You have already reviewed '{book_to_review.title}'"}
                ),
                400,
            )

    # Add review
    user.reviews.append(review)

    return (
        jsonify(
            {
                "message": f"Review added for '{book_to_review.title}'",
                "review": review,
            }
        ),
        200,
    )


def get_reviews(user):
    """Get all reviews of books by the user
    Arguments:
    user: class User
    Returns:
    tuple: (jsonified response, status_code)
    """

    if not user.reviews:
        return jsonify({"message": "You have not reviewed any books yet"}), 404

    return jsonify({"reviews": [review for review in user.reviews]}), 200


def delete_review(user, book_id):
    """Deleting a user's review of a given book
    Arguments:
    user: class User
    book_id: int, ID of the book to delete review
    Returns:
    tuple: (jsonified response, status_code)
    Raises:
    ValueError: If book is not provided
    """

    if not book:
        return jsonify({"message": "Please provide a book to delete"}), 400

    # Find the book in personal library
    book_to_delete = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_delete = book
            break

    if not book_to_delete:
        return (
            jsonify(
                {
                    "message": f"Book with ID {book_id} not found in your personal library"
                }
            ),
            404,
        )

    # Check if user has reviewed the book
    for review in user.reviews:
        if review.id == book_id:
            user.reviews.remove(review)
            return (
                jsonify(
                    {"message": f"Review for '{book_to_delete.title}' has been deleted"}
                ),
                200,
            )

    return (
        jsonify({"message": f"You have not reviewed '{book_to_delete.title}'"}),
        400,
    )


def delete_book_from_library(user, book_id: int):
    """Delete a book from the user's personal library
    Arguments:
    user: class User
    book_id: int, ID of the book to delete
    Returns:
    tuple: (jsonified response, status_code)
    """
    # Find the book in personal library
    book_to_delete = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_delete = book
            break

    if not book_to_delete:
        return (
            jsonify({"message": f"Book with ID {book_id} not found in your library"}),
            404,
        )

    # Remove the book
    user.personal_library.remove(book_to_delete)

    return (
        jsonify(
            {"message": f"'{book_to_delete.title}' has been removed from your library"}
        ),
        200,
    )


def update_status(user, book_id: int, new_status: str):
    """Updating a user's status on a particular book given a book id
    Arguments:
    user: class User
    book_id: int, ID of the book who's status will be updated
    new_status: string, new status to be updated

    Returns:
    tuple: (jsonified response, status_code)
        - 200: If the status is successfully updated.

    Raises:
    tuple: (jsonified response, status_code)
        - 400: If `new_status` is invalid.
        - 404: If the book with given `book_id` is not found in the user's library.
        - 500: If there's a database error

    """

    # Checking for valid status
    if new_status not in ["Want to Read", "Reading", "Read"]:
        return (
            jsonify({"message": f"Invalid reading status provided {new_status}"}),
            400,
        )

    book_to_update = None
    # finding book
    for book in user.personal_library:
        if book.id == book_id:
            book_to_update = book
            break
    # endfor

    if not book_to_update:
        return (
            jsonify({"message": f"Book with ID {book_id} not found in your library"}),
            404,
        )

    book_to_update.status = new_status
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE user_books
                SET status = ?
                WHERE user_id = ? AND book_id = ?
                """,
                (new_status, user.id, book_id),
            )
            conn.commit()

        return (
            jsonify(
                {
                    "message": f"Status of '{book_to_update.title}' has been updated to '{new_status}'",
                    "book": book_to_update.to_dict(),
                }
            ),
            200,
        )

    except sqlite3.Error as e:
        logger.error("Database error while updating book status: %s", str(e))
        return jsonify({"message": "Error updating book status"}), 500
