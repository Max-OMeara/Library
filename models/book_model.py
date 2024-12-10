from typing import Dict, Optional


class Book:
    id: int
    title: str
    author: str
    isbn: Optional[str]
    status: str

    def __init__(
        self,
        id: int,
        title: str,
        author: str = "Unknown",
        isbn: Optional[str] = None,
        status: str = "Want to Read",
    ):
        self.id = id
        self.title = title
        self.author = author
        self.isbn = isbn
        self.status = status

    def to_dict(self) -> Dict:
        """Convert book object to dictionary representation
        Returns:
            Dict: Book data in dictionary format
        """
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "isbn": self.isbn,
            "status": self.status if hasattr(self, "status") else None,
        }

    def __str__(self) -> str:
        """String representation of the book
        Returns:
            str: Formatted string with book details
        """
        return f"'{self.title}' by {self.author} ({self.status})"


# enddef
