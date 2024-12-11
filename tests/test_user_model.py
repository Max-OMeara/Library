
import sys
import os
import pytest
import hashlib
from contextlib import contextmanager
from flask import jsonify
import sqlite3

# Add the project root to sys.path to ensure modules are discoverable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.user_model import User, Review
from models.book_model import Book

@pytest.fixture
def sample_user():
    return User(id=1, username='test_user', password_hash='password_hash', salt='salt')
# end sample_user fixture

@pytest.fixture
def sample_review(sample_book):
    return Review(sample_book.id, sample_book.title, "Great Read")

@pytest.fixture
def sample_book():
    return Book(id=1, title="Animal Farm", author="George Orwell", isbn="1234567890", status="Read")

@pytest.fixture
def mock_cursor(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_conn.commit.return_value = None

    # Mock the get_db_connection context manager from user_model
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("models.user_model.get_db_connection", mock_get_db_connection)
    mocker.patch("music_collection.models.user_model.get_db_connection", mock_get_db_connection)

    return mock_cursor  # Return the mock cursor so we can set expectations per test
# end mock_cursor fixture

# tests for review class
def test_to_dict(sample_review, sample_book):
    """Tests whether a to_dict returns a dictionary"""
    a = sample_review.to_dict()
    assert len(a)==3
    assert a['book_id'] == 1
    assert a['book_title'] == sample_review.book_title
    assert a['review_text'] == sample_review.review_text
#endtest

# tests for user class
def test_set_password(mocker):
    """Tests setting a password with a mocked salt"""
    # Arrange
    # Mock os.urandom to return 64 bytes of 'x' (0x78)
    mock_salt = b'x' * 64
    mocker.patch('os.urandom', return_value=mock_salt)

    user = User(id=1, username='test_user')
    user.set_password('1234')

    # The salt should be 'x' in hex (78) repeated 64 times
    expected_salt = '78' * 64

    expected_hash = hashlib.sha512(f"1234{expected_salt}".encode()).hexdigest()

    assert user.salt == expected_salt, "Salt does not match the expected mocked value."
    assert user.password_hash == expected_hash, "Password hash does not match the expected value."
    
    # Ensure set_password returns None
    assert user.set_password('1234') is None
# endtest_set_password

def test_update_password(mocker):
    """Tests updating a password with a mocked salt"""
    # Arrange
    # Mock os.urandom to return 64 bytes of 'x' (0x78)
    mock_salt = b'x' * 64
    mocker.patch('os.urandom', return_value=mock_salt)

    user = User(id=1, username='test_user')
    user.set_password('1234')

    # The salt should be 'x' in hex (78) repeated 64 times
    expected_salt = '78' * 64

    expected_hash = hashlib.sha512(f"1234{expected_salt}".encode()).hexdigest()

    assert user.salt == expected_salt, "Salt does not match the expected mocked value."
    assert user.password_hash == expected_hash, "Password hash does not match the expected value."

    # Act
    user.update_password('12345')

    # The salt should be 'x' in hex (78) repeated 64 times
    expected_salt = '78' * 64

    expected_hash = hashlib.sha512(f"12345{expected_salt}".encode()).hexdigest()

    assert user.salt == expected_salt, "Salt does not match the expected mocked value."
    assert user.password_hash == expected_hash, "Password hash does not match the expected value."
# endtest_update_password

def test_check_password(sample_user):
    """Tests checking a password"""
    a = sample_user.check_password('1234')
    b = sample_user.check_password('12344')

    assert a == True
    assert b == False

# endtest_check_password

def test_get_user_by_username(mock_cursor, sample_user):
    """Tests getting a user by username"""
    mock_cursor.fetchone.return_value = (1, 'test_user')
    user = get_user_by_username('test_user')
    assert user.id == 1
    assert user.username == 'test_user'
    assert user.password_hash == 'password_hash'
    assert user.salt == 'salt'
# endtest_get_user_by_username

def test_add_book_personal_library(sample_user, sample_book):
    """Tests adding a book to the personal library"""
    response, status_code = add_book_personal_library(sample_user, sample_book)
    assert status_code == 200
    assert response == jsonify({"message": "Book added to personal library."})
    assert sample_book in sample_user.library
    assert "message" in response
    assert "book" in response
    assert response["book"]["title"] == "Animal Farm"
# endtest_add_book_personal_library

def add_book_favorite_books(sample_user, sample_book):
    """Tests adding a book to the favorite books"""
    response, status_code = add_book_favorite_books(sample_user, sample_book)
    assert status_code == 200
    assert response == jsonify({"message": "Book added to favorite books."})
    assert sample_book in sample_user.favorite_books
    assert "message" in response
    assert "book" in response
    assert response["book"]["title"] == "Animal Farm"
# endtest_add_book_favorite_books

# Additional Tests for User Class
def test_get_library(sample_user):
    """Tests getting the user's library"""
    response, status_code = get_library(sample_user)
    assert status_code == 200
    assert response == jsonify(sample_user.library)
    assert len(response.json) == 0
# endtest_get_library

def test_delete_book_from_library(sample_user, sample_book):
    """Tests deleting a book from the personal library"""
    sample_user.library.append(sample_book)
    response, status_code = delete_book_from_library(sample_user, sample_book)
    assert status_code == 200
    assert response == jsonify({"message": "Book deleted from personal library."})
    assert sample_book not in sample_user.library
    assert "message" in response
    assert "book" in response
    assert response["book"]["title"] == "Animal Farm"
# endtest_delete_book_from_library

def test_update_status(sample_user, sample_book):
    """Tests updating the status of a book in the personal library"""
    sample_user.library.append(sample_book)
    response, status_code = update_status(sample_user, sample_book, "Reading")
    assert status_code == 200
    assert response == jsonify({"message": "Book status updated."})
    assert sample_book.status == "Reading"
    assert "message" in response
    assert "book" in response
    assert response["book"]["title"] == "Animal Farm"
# endtest_update_status


# def add_book_review
def test_add_book_review(sample_user, sample_book):
    """Tests adding a review for a book"""
    response, status_code = add_book_review(sample_user, sample_book, "Great Read")
    assert status_code == 200
    assert response == jsonify({"message": "Review added."})
    assert sample_book in sample_user.reviews
    assert "message" in response
    assert "book" in response
    assert response["book"]["title"] == "Animal Farm"
# endtest_add_book_review

# def get_reviews
def test_get_reviews(sample_user):
    """Tests getting the user's reviews"""
    response, status_code = get_reviews(sample_user)
    assert status_code == 200
    assert response == jsonify(sample_user.reviews)
    assert len(response.json) == 0
# endtest_get_reviews

# def delete_review
def test_delete_review(sample_user, sample_review):
    """Tests deleting a review"""
    sample_user.reviews.append(sample_review)
    response, status_code = delete_review(sample_user, sample_review)
    assert status_code == 200
    assert response == jsonify({"message": "Review deleted."})
    assert sample_review not in sample_user.reviews
    assert "message" in response
    assert "review" in response
    assert response["review"]["book_title"] == "Animal Farm"
# endtest_delete_review

if __name__ == "__main__":
    pytest.main()
