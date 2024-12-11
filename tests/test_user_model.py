from models.user_model import *
from models.book_model import *
import pytest
import hashlib



@pytest.fixture
def sample_review(sample_book):
    return Review(sample_book.id, sample_book.title, "Great Read")

@pytest.fixture
def sample_book():
    return Book(id=1, title="Animal Farm", author="George Orwell", isbn="1234567890", status="Read")

@pytest.fixture
def sample_user():
    example_user = User(1, 'example_user')
    example_user.set_password("1234")
    return example_user
#end fixture

@pytest.fixture
def mock_cursor(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_conn.commit.return_value = None

    # Mock the get_db_connection context manager from sql_utils
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("models.song_model.get_db_connection", mock_get_db_connection)
    mocker.patch("music_collection.models.song_model.get_db_connection", mock_get_db_connection)
    
    return mock_cursor  # Return the mock cursor so we can set expectations per test




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

def test_set_password(sample_user):
    """Tests setting a password"""
    p = '1234'
    assert sample_user.password_hash == hashlib.sha512(
            f"{p}{sample_user.salt}".encode()
        ).hexdigest()
    a = sample_user.set_password('1234')
    assert a == None

def test_check_password(sample_user):
    """Tests checking a password"""
    a = sample_user.check_password('1234')
    b = sample_user.check_password('12344')

    assert a == True
    assert b == False

# def create_user_account
# def get_user_bu_username
# def update_password
#def get_library(sample_user):


def test_add_book_personal_library(sample_user, sample_book):
    response, status_code = add_book_personal_library(sample_user, sample_book)
    assert status_code == 200
    #assert response == jsonify*
#def add_book_favorite_books
# def add_book_review
# def get_reviews
# def delete_review
# def delete_book_from_library
# def update_status

