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


class Review:
    def __init__(self, book_id: int, book_title: str, review_text: str):
        self.book_id = book_id
        self.book_title = book_title
        self.review_text = review_text

    def to_dict(self):
        return {
            "book_id": self.book_id,
            "book_title": self.book_title,
            "review_text": self.review_text,
        }


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

        try:
            self.salt = os.urandom(64).hex()
            self.password_hash = hashlib.sha512(
                f"{password}{self.salt}".encode()
            ).hexdigest()
            logger.info("Password successfully hashed for user: %s", self.username)
        except Exception as e:
            logger.error(
                "Error hashing password for user %s: %s", self.username, str(e)
            )
            raise

    def check_password(self, password: str) -> bool:
        """Verify the password against stored hash using SHA-512
        Args:
            password: The plain text password to verify
        Returns:
            bool: True if password matches, False otherwise
        """
        try:
            if not self.salt or not self.password_hash:
                logger.warning(
                    "Missing salt or password hash for user: %s", self.username
                )
                return False

            password_to_check = hashlib.sha512(
                f"{password}{self.salt}".encode()
            ).hexdigest()

            is_match = self.password_hash == password_to_check
            if is_match:
                logger.info(
                    "Successful password verification for user: %s", self.username
                )
            else:
                logger.warning(
                    "Failed password verification attempt for user: %s", self.username
                )

            return is_match

        except Exception as e:
            logger.error(
                "Error checking password for user %s: %s", self.username, str(e)
            )
            return False

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
                    logger.info("Successfully retrieved user: %s", username)
                    return user

                logger.warning("User not found: %s", username)
                return None

        except sqlite3.Error as e:
            logger.error(
                "Database error while retrieving user %s: %s", username, str(e)
            )
            return None

    def update_password(self, new_password: str):
        """Update the user's password with new hash and salt
        Args:
            new_password: The new plain text password
        Returns:
            tuple: (message dict, status code)
        """
        try:
            # set_password already includes logging for the hashing process
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

                logger.info(
                    "Password successfully updated in database for user: %s",
                    self.username,
                )
                return jsonify({"message": "Password updated successfully"}), 200

        except sqlite3.Error as e:
            logger.error(
                "Database error updating password for user %s: %s",
                self.username,
                str(e),
            )
            return jsonify({"message": "Error updating password"}), 500
        except Exception as e:
            logger.error(
                "Unexpected error updating password for user %s: %s",
                self.username,
                str(e),
            )
            return jsonify({"message": "Error updating password"}), 500

    @staticmethod
    def delete_user_account(username: str) -> tuple:
        """Delete a user account and all associated data.

        Args:
            username: The username of the account to delete

        Returns:
            tuple: A tuple containing (response, status_code) where:
                - response: JSON object with success or error message
                - status_code: HTTP status code
                    200: Success (account deleted)
                    404: Not found (user doesn't exist)
                    500: Server error (database error)
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()

                # First, get the user ID
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                user_data = cursor.fetchone()

                if not user_data:
                    logger.warning("Attempt to delete non-existent user: %s", username)
                    return jsonify({"message": f"User '{username}' not found"}), 404

                user_id = user_data[0]

                # Delete all associated data
                # Delete reviews
                cursor.execute("DELETE FROM reviews WHERE user_id = ?", (user_id,))

                # Delete from favorite books
                cursor.execute(
                    "DELETE FROM favorite_books WHERE user_id = ?", (user_id,)
                )

                # Delete from personal library
                cursor.execute("DELETE FROM user_books WHERE user_id = ?", (user_id,))

                # Finally, delete the user
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

                conn.commit()

                logger.info(
                    "Successfully deleted user account and all associated data for: %s",
                    username,
                )
                return (
                    jsonify(
                        {
                            "message": f"Account and all associated data deleted for {username}"
                        }
                    ),
                    200,
                )

        except sqlite3.Error as e:
            logger.error(
                "Database error deleting user account %s: %s", username, str(e)
            )
            return jsonify({"message": "Error deleting account"}), 500


def get_library(user):
    """Get all books in the user's library organized by status and favorites
    Arguments:
    user: class User
    Returns:
    tuple: (jsonified response, status_code)
    """
    try:
        library = {
            "books": {},
            "favorites": [book.to_dict() for book in user.favorite_books],
        }

        # Organize books by status
        for book in user.personal_library:
            if book.status not in library["books"]:
                library["books"][book.status] = []
            library["books"][book.status].append(book.to_dict())

        logger.info(
            "Successfully retrieved library for user %s: %d books, %d favorites",
            user.username,
            len(user.personal_library),
            len(user.favorite_books),
        )
        return jsonify(library), 200

    except Exception as e:
        logger.error("Error retrieving library for user %s: %s", user.username, str(e))
        return jsonify({"message": "Error retrieving library"}), 500


def add_book_personal_library(user, book_data: dict):
    """Add a book to the user's personal library using OpenLibrary API.

    Args:
        user: User instance to add the book to
        book_data: dict containing book information with keys:
            title (str): Required. The title of the book to search for
            author (str): Optional. The author's name to narrow search

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with message and book data
            - status_code: HTTP status code
                200: Success (book added)
                300: Multiple matches found
                400: Bad request (missing title or duplicate book)
                404: Book not found
                500: OpenLibrary API error
    """
    if not book_data.get("title"):
        logger.warning("Attempt to add book without title by user: %s", user.username)
        return {"message": "Please provide a book title"}, 400

    # Set up OpenLibrary API search parameters
    params = {
        "title": book_data["title"],
        "fields": "title,author_name,isbn",
        "limit": 5,
    }

    if "author" in book_data:
        params["author"] = book_data["author"]
        logger.info(
            "Searching for book '%s' by '%s' for user: %s",
            book_data["title"],
            book_data["author"],
            user.username,
        )
    else:
        logger.info(
            "Searching for book '%s' for user: %s", book_data["title"], user.username
        )

    # Search OpenLibrary API
    try:
        response = session.get(
            "https://openlibrary.org/search.json",
            params=params,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("OpenLibrary API error for user %s: %s", user.username, str(e))
        return {"message": "Failed to fetch from OpenLibrary"}, 500

    books = response.json().get("docs", [])

    if not books:
        logger.info(
            "No books found with title '%s' for user: %s",
            book_data["title"],
            user.username,
        )
        return {"message": "No books found with that title"}, 404

    if len(books) == 1 or "author" in book_data:
        # Add first matching book
        book = books[0]
        book_title = book.get("title", "Unknown")
        book_author = book.get("author_name", ["Unknown"])[0]

        # Check for duplicate books
        for existing_book in user.personal_library:
            if (
                existing_book.title.lower() == book_title.lower()
                and existing_book.author.lower() == book_author.lower()
            ):
                logger.info(
                    "Duplicate book attempt '%s' by '%s' for user: %s",
                    book_title,
                    book_author,
                    user.username,
                )
                return {
                    "message": f"'{book_title}' by {book_author} is already in your library with status: '{existing_book.status}'",
                    "book": existing_book.to_dict(),
                }, 400

        # If no duplicate found, add the new book
        new_book = Book(
            id=len(user.personal_library) + 1,
            title=book_title,
            author=book_author,
            isbn=book.get("isbn", [None])[0] if book.get("isbn") else None,
            status="Want to Read",
        )
        user.personal_library.append(new_book)

        logger.info(
            "Successfully added book '%s' by '%s' for user: %s",
            new_book.title,
            new_book.author,
            user.username,
        )
        return {
            "message": f"Success! '{new_book.title}' by {new_book.author} has been added to your library.",
            "book": new_book.to_dict(),
        }, 200

    # Multiple books found
    logger.info(
        "Multiple books (%d) found with title '%s' for user: %s",
        len(books),
        book_data["title"],
        user.username,
    )
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
    """Add a book from personal library to favorite books and mark as Read.

    Args:
        user: User instance to add the favorite book to
        book_id: ID of the book to add to favorites

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with message and book data
            - status_code: HTTP status code
                200: Success (book added to favorites)
                400: Bad request (book already in favorites)
                404: Book not found in personal library
    """

    # Find the book in personal library
    book_to_favorite = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_favorite = book
            break

    if not book_to_favorite:
        logger.warning(
            "Attempt to favorite non-existent book (ID: %d) by user: %s",
            book_id,
            user.username,
        )
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
            logger.info(
                "Duplicate favorite attempt for book '%s' by user: %s",
                book.title,
                user.username,
            )
            return (
                jsonify({"message": f"'{book.title}' is already in your favorites"}),
                400,
            )

    # Update book status to "Read"
    book_to_favorite.status = "Read"

    # Add to favorites
    user.favorite_books.append(book_to_favorite)

    logger.info(
        "Book '%s' added to favorites for user: %s",
        book_to_favorite.title,
        user.username,
    )
    return (
        jsonify(
            {
                "message": f"'{book_to_favorite.title}' has been added to your favorites and marked as Read",
                "book": book_to_favorite.to_dict(),
            }
        ),
        200,
    )


def add_book_review(user, review_text: str, book_id: int):
    """Adding a user's review of a particular book
    Arguments:
    user: class User
    review_text: string, review to be added
    book_id: int, ID of the book to review
    Returns:
    tuple: (jsonified response, status_code)
    """

    if not review_text:
        logger.warning("Attempt to add empty review by user: %s", user.username)
        return jsonify({"message": "Please provide a review"}), 400

    # Find the book in personal library
    book_to_review = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_review = book
            break

    if not book_to_review:
        logger.warning(
            "Attempt to review non-existent book (ID: %d) by user: %s",
            book_id,
            user.username,
        )
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
        if review.book_id == book_id:
            logger.info(
                "Duplicate review attempt for book '%s' by user: %s",
                book_to_review.title,
                user.username,
            )
            return (
                jsonify(
                    {"message": f"You have already reviewed '{book_to_review.title}'"}
                ),
                402,
            )

    # Create a new review
    new_review = Review(
        book_id=book_id, book_title=book_to_review.title, review_text=review_text
    )

    # Add review
    user.reviews.append(new_review)

    logger.info(
        "Review added for book '%s' by user: %s", book_to_review.title, user.username
    )
    return (
        jsonify(
            {
                "message": f"Review added for '{book_to_review.title}'",
                "review": new_review.to_dict(),
            }
        ),
        200,
    )


def get_reviews(user):
    """Get all reviews of books by the user.

    Args:
        user: User instance whose reviews to retrieve

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with list of reviews or message
            - status_code: HTTP status code
                200: Success (reviews found)
                404: Not found (no reviews exist)
    """

    if not user.reviews:
        logger.info("No reviews found for user: %s", user.username)
        return jsonify({"message": "You have not reviewed any books yet"}), 404

    logger.info("Retrieved %d reviews for user: %s", len(user.reviews), user.username)
    return jsonify({"reviews": [review.to_dict() for review in user.reviews]}), 200


def delete_review(user, book_id: int):
    """Deleting a user's review of a given book
    Arguments:
    user: class User
    book_id: int, ID of the book to delete review
    Returns:
    tuple: (jsonified response, status_code)
    Raises:
    ValueError: If book is not provided
    """

    if not book_id:
        logger.warning(
            "Attempt to delete review without book_id by user: %s", user.username
        )
        return jsonify({"message": "Please provide a book to delete"}), 400

    # Find the book in personal library
    book_to_delete = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_delete = book
            break

    if not book_to_delete:
        logger.warning(
            "Attempt to delete review for non-existent book (ID: %d) by user: %s",
            book_id,
            user.username,
        )
        return (
            jsonify(
                {
                    "message": f"Book with ID {book_id} not found in your personal library"
                }
            ),
            404,
        )

    # Check if user has reviewed the book
    review_to_delete = None
    for review in user.reviews:
        if review.book_id == book_id:
            review_to_delete = review
            break

    if review_to_delete:
        user.reviews.remove(review_to_delete)
        logger.info(
            "Review deleted for book '%s' by user: %s",
            book_to_delete.title,
            user.username,
        )
        return (
            jsonify(
                {"message": f"Review for '{book_to_delete.title}' has been deleted"}
            ),
            200,
        )

    logger.info(
        "Attempt to delete non-existent review for book '%s' by user: %s",
        book_to_delete.title,
        user.username,
    )
    return (
        jsonify({"message": f"You have not reviewed '{book_to_delete.title}'"}),
        400,
    )


def delete_book_from_library(user, book_id: int):
    """Delete a book from the user's personal library.

    Args:
        user: User instance whose library to modify
        book_id: ID of the book to delete

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with success or error message
            - status_code: HTTP status code
                200: Success (book deleted)
                404: Not found (book not in library)
    """
    # Find the book in personal library
    book_to_delete = None
    for book in user.personal_library:
        if book.id == book_id:
            book_to_delete = book
            break

    if not book_to_delete:
        logger.warning(
            "Attempt to delete non-existent book (ID: %d) from library of user: %s",
            book_id,
            user.username,
        )
        return (
            jsonify({"message": f"Book with ID {book_id} not found in your library"}),
            404,
        )

    # Remove the book
    user.personal_library.remove(book_to_delete)

    logger.info(
        "Book '%s' removed from library of user: %s",
        book_to_delete.title,
        user.username,
    )
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
        logger.warning(
            "Invalid status '%s' provided for user %s, book ID %d",
            new_status,
            user.username,
            book_id,
        )
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

    if not book_to_update:
        logger.warning(
            "Attempt to update status for non-existent book (ID: %d) by user: %s",
            book_id,
            user.username,
        )
        return (
            jsonify({"message": f"Book with ID {book_id} not found in your library"}),
            404,
        )

    old_status = book_to_update.status
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

        logger.info(
            "Updated status of book '%s' from '%s' to '%s' for user: %s",
            book_to_update.title,
            old_status,
            new_status,
            user.username,
        )
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
        logger.error(
            "Database error while updating book status for user %s: %s",
            user.username,
            str(e),
        )
        return jsonify({"message": "Error updating book status"}), 500
