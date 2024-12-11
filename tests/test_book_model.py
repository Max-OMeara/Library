import pytest
from models.book_model import *

@pytest.fixture
def test_book_initialization():
    book = Book(id=1, title="Animal Farm", author="George Orwell", isbn="1234567890", status="Read")
    assert book.id == 1
    assert book.title == "Animal Farm"
    assert book.author == "George Orwell"
    assert book.isbn == "1234567890"
    assert book.status == "Read"
    return book


@pytest.fixture
def test_book_to_dict():
    book = Book(id=3, title="Fahrenheit 451", author="Ray Bradbury", isbn="0987654321", status="Reading")
    book_dict = book.to_dict()
    assert book_dict == {
        "id": 3,
        "title": "Fahrenheit 451",
        "author": "Ray Bradbury",
        "isbn": "0987654321",
        "status": "Reading"
    }

@pytest.fixture
def test_book_str():
    book = Book(id=4, title="The Great Gatsby", author="F. Scott Fitzgerald", status="Read")
    assert str(book) == "'The Great Gatsby' by F. Scott Fitzgerald (Read)"
    return book

if __name__ == "__main__":
    pytest.main()