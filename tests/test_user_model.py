import pytest
import hashlib
from flask import Flask
from models.user_model import User, Review
from models.book_model import Book
import sqlite3

##################################################
# Fixtures
##################################################


@pytest.fixture
def sample_user(mocker):
    """Fixture to provide a new instance of User for testing."""
    # Mock os.urandom to return a predictable value for consistent testing
    mock_salt = b"1" * 64
    mocker.patch("os.urandom", return_value=mock_salt)

    user = User(id=1, username="test_user")
    user.set_password("1234")  # This will set salt and password_hash
    return user


@pytest.fixture
def sample_book():
    """Fixture to provide a sample book for testing."""
    return Book(
        id=1,
        title="Animal Farm",
        author="George Orwell",
        isbn="1234567890",
        status="Want to Read",
    )


@pytest.fixture
def sample_book2():
    """Fixture to provide a second sample book for testing."""
    return Book(
        id=2,
        title="1984",
        author="George Orwell",
        isbn="0987654321",
        status="Want to Read",
    )


@pytest.fixture
def sample_review(sample_book):
    """Fixture to provide a sample review for testing."""
    return Review(sample_book.id, sample_book.title, "Great Read")


@pytest.fixture
def mock_db(mocker):
    """Mock database connection and cursor for testing."""
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Configure the mock connection to work as a context manager
    mock_conn.__enter__ = mocker.Mock(return_value=mock_conn)
    mock_conn.__exit__ = mocker.Mock(return_value=None)

    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.execute.return_value = None
    mock_conn.commit.return_value = None

    mocker.patch("models.user_model.sqlite3.connect", return_value=mock_conn)
    return mock_cursor


@pytest.fixture
def app():
    """Create a Flask application context"""
    app = Flask(__name__)
    with app.app_context():
        yield app


##################################################
# User Account Management Test Cases
##################################################


def test_user_initialization():
    """Test basic user initialization."""
    user = User(id=1, username="test_user")
    assert user.id == 1
    assert user.username == "test_user"
    assert user.salt is None
    assert user.password_hash is None
    assert isinstance(user.personal_library, list)
    assert isinstance(user.favorite_books, list)
    assert isinstance(user.reviews, list)


def test_set_password(mocker):
    """Test setting a user's password."""
    mock_salt = b"1" * 64
    mocker.patch("os.urandom", return_value=mock_salt)

    user = User(username="test_user")
    user.set_password("1234")

    expected_salt = mock_salt.hex()
    expected_hash = hashlib.sha512(f"1234{expected_salt}".encode()).hexdigest()

    assert user.salt == expected_salt
    assert user.password_hash == expected_hash


def test_check_password(sample_user):
    """Test password verification."""
    assert sample_user.check_password("1234") is True
    assert sample_user.check_password("wrong") is False


def test_create_user_account(app, mock_db, mocker):
    """Test user account creation."""
    mock_db.lastrowid = 1
    # Mock jsonify to return a dict instead of Response object
    mock_jsonify = mocker.patch("models.user_model.jsonify", side_effect=lambda x: x)

    response, status_code = User.create_user_account("test_user", "1234")

    assert status_code == 200
    assert "Account created successfully" in response["message"]


def test_create_duplicate_user_account(app, mock_db, mocker):
    """Test creating a duplicate user account."""
    # Mock jsonify to return a dict instead of Response object
    mock_jsonify = mocker.patch("models.user_model.jsonify", side_effect=lambda x: x)
    # First mock a successful creation to simulate existing user
    mock_db.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")

    response, status_code = User.create_user_account("test_user", "1234")

    assert status_code == 400
    assert "already exists" in response["message"]


def test_get_user_by_username(mock_db):
    """Test retrieving a user by username."""
    mock_db.fetchone.return_value = (1, "test_user", "hashed_password", "salt")

    user = User.get_user_by_username("test_user")

    assert user is not None
    assert user.id == 1
    assert user.username == "test_user"
    assert user.salt == "salt"
    # endtest_get_user_by_username
    assert user.username == "test_user"
    assert user.password_hash == "hashed_password"
    assert user.salt == "salt"


def test_get_nonexistent_user(mock_db):
    """Test retrieving a non-existent user."""
    mock_db.fetchone.return_value = None

    user = User.get_user_by_username("nonexistent")
    assert user is None


def test_update_password(sample_user, mock_db, mocker):
    """Test updating a user's password."""
    # Mock jsonify
    mock_jsonify = mocker.patch("models.user_model.jsonify", side_effect=lambda x: x)

    response, status_code = sample_user.update_password("new_password")

    assert status_code == 200
    assert "Password updated successfully" in response["message"]


def test_delete_user_account(app, mock_db, mocker):
    """Test deleting a user account."""
    # Mock jsonify to return a dict instead of Response object
    mock_jsonify = mocker.patch("models.user_model.jsonify", side_effect=lambda x: x)
    mock_db.fetchone.return_value = (1,)

    response, status_code = User.delete_user_account("test_user")

    assert status_code == 200
    assert "Account and all associated data deleted" in response["message"]


##################################################
# Library Management Test Cases
##################################################


def test_add_book_to_library(sample_user, sample_book):
    """Test adding a book to user's library."""
    sample_user.personal_library.append(sample_book)

    assert len(sample_user.personal_library) == 1
    assert sample_user.personal_library[0].id == sample_book.id
    assert sample_user.personal_library[0].title == sample_book.title


def test_add_duplicate_book_to_library(sample_user, sample_book):
    """Test adding a duplicate book to the library."""
    # Add book first time
    sample_user.personal_library.append(sample_book)
    initial_length = len(sample_user.personal_library)

    # Try to add the same book again
    sample_user.personal_library.append(sample_book)

    assert len(sample_user.personal_library) == initial_length + 1


def test_remove_book_from_library(sample_user, sample_book):
    """Test removing a book from the library."""
    sample_user.personal_library.append(sample_book)
    initial_length = len(sample_user.personal_library)

    sample_user.personal_library.remove(sample_book)
    assert len(sample_user.personal_library) == initial_length - 1


##################################################
# Favorites Management Test Cases
##################################################


def test_add_book_to_favorites(sample_user, sample_book):
    """Test adding a book to favorites."""
    sample_user.favorite_books.append(sample_book)

    assert len(sample_user.favorite_books) == 1
    assert sample_user.favorite_books[0].id == sample_book.id
    assert sample_user.favorite_books[0].title == sample_book.title


def test_remove_book_from_favorites(sample_user, sample_book):
    """Test removing a book from favorites."""
    sample_user.favorite_books.append(sample_book)
    initial_length = len(sample_user.favorite_books)

    sample_user.favorite_books.remove(sample_book)
    assert len(sample_user.favorite_books) == initial_length - 1


##################################################
# Review Management Test Cases
##################################################


def test_add_review(sample_user, sample_review):
    """Test adding a review."""
    sample_user.reviews.append(sample_review)

    assert len(sample_user.reviews) == 1
    assert sample_user.reviews[0].book_id == sample_review.book_id
    assert sample_user.reviews[0].review_text == sample_review.review_text


def test_remove_review(sample_user, sample_review):
    """Test removing a review."""
    sample_user.reviews.append(sample_review)
    initial_length = len(sample_user.reviews)

    sample_user.reviews.remove(sample_review)
    assert len(sample_user.reviews) == initial_length - 1


def test_review_to_dict(sample_review):
    """Test review to dictionary conversion."""
    review_dict = sample_review.to_dict()

    assert isinstance(review_dict, dict)
    assert review_dict["book_id"] == sample_review.book_id
    assert review_dict["book_title"] == sample_review.book_title
    assert review_dict["review_text"] == sample_review.review_text
