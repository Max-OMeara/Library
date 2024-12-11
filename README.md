# Library API Documentation

## Authentication Routes

### Create Account

**Route:** `/create-account`

- **Method:** POST
- **Purpose:** Creates a new user account with a username and password.
- **Request Body:**

  ```json
  {
      "username": "newuser123",
      "password": "securepassword"
  }
  ```

- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
        "message": "Account created successfully for newuser123"
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "Please provide both username and password"
    }
    ```

  - **Code:** 400

    ```json
    {
        "message": "User with username 'newuser123' already exists"
    }
    ```

### Login

**Route:** `/login`

- **Method:** POST
- **Purpose:** Authenticates a user with their credentials
- **Request Body:**

  ```json
  {
      "username": "newuser123",
      "password": "securepassword"
  }
  ```
  
- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
        "message": "Welcome back, newuser123!"
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "Please provide both username and password"
    }
    ```

  - **Code:** 401

    ```json
    {
        "message": "Invalid username or password"
    }
    ```

### Update Password

**Route:** `/update-password`

- **Method:** PUT
- **Purpose:** Updates the password for an existing user account
- **Request Body:**

  ```json
  {
      "username": "newuser123",
      "old_password": "securepassword",
      "new_password": "newpassword123"
  }
  ```

- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
        "message": "Password updated successfully"
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "Please provide username, old_password, and new_password"
    }
    ```

  - **Code:** 401

    ```json
    {
        "message": "Invalid username or password"
    }
    ```

  - **Code:** 500

    ```json
    {
        "message": "Error updating password"
    }
    ```

### Add favorite book

**Route:** `/api/add-book-favorite-books`

- **Method:** POST
- **Purpose:** Route to add a book from personal library onto a user's favorite
  books list and mark it as read
- **Request Body:**

  ```json
    {
    "username" :"(String): User's chosen username."
    "book_id" :"(Int) Id of book that will be added to favorite's list"
    }
  ```

- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
      "message": "{book_to_favorite.title} has been added to your favorites and marked as Read"
      "review": "Custom Message"
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "{book.title} is already in your favorites"
    }
    ```

- **Code:** 404

  ```json
  {
      "message": "Book with ID {book_id} not found in your personal library"
  }
  ```

## Library Routes

### Get Library

**Route:** `/api/get-library`

- **Method:** GET
- **Purpose:** Retrieves all books in a user's library organized by reading
  status
- **Query Parameters:**
  - `username` (required): The username of the library owner
- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
        "books": {
            "Want to Read": [
                {
                    "id": 1,
                    "title": "The Great Gatsby",
                    "author": "F. Scott Fitzgerald",
                    "isbn": "9780743273565",
                    "status": "Want to Read"
                }
            ],
            "Reading": [],
            "Read": []
        }
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "Please provide a username"
    }
    ```

  - **Code:** 404

    ```json
    {
        "message": "User not found"
    }
    ```

### Add Book

**Route:** `/api/add-book`

- **Method:** POST
- **Purpose:** Adds a book to the user's library using the OpenLibrary API
- **Request Body:**

  ```json
  {
      "username": "newuser123",
      "title": "The Great Gatsby",
      "author": "F. Scott Fitzgerald"  // optional
  }
  ```

- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
        "message": "Success! 'The Great Gatsby' by F. Scott Fitzgerald has been added to your library.",
        "book": {
            "id": 1,
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "isbn": "9780743273565",
            "status": "Want to Read"
        }
    }
    ```

- **Multiple Matches Response:**
  - **Code:** 300
  - **Content:**

    ```json
    {
        "message": "I found 3 books with that title. Please specify the author's name to help me find the right one:",
        "books": [
            {
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "isbn": "9780743273565"
            },
            {
                "title": "The Great Gatsby: A Graphic Novel Adaptation",
                "author": "K. Woodman-Maynard",
                "isbn": "9781536217650"
            }
        ]
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "Please provide a username"
    }
    ```

  - **Code:** 400

    ```json
    {
        "message": "Please provide a book title"
    }
    ```

  - **Code:** 404

    ```json
    {
        "message": "User not found"
    }
    ```

  - **Code:** 404

    ```json
    {
        "message": "No books found with that title"
    }
    ```

  - **Code:** 500

    ```json
    {
        "message": "Failed to fetch from OpenLibrary"
    }
    ```

### Delete Book

**Route:** `/api/delete-book/<book_id>`

- **Method:** DELETE
- **Purpose:** Removes a specific book from the user's library
- **URL Parameters:**
  - `book_id` (required): The ID of the book to delete
- **Query Parameters:**
  - `username` (required): The username of the library owner
- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
        "message": "'The Great Gatsby' has been removed from your library"
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "Please provide a username"
    }
    ```

  - **Code:** 404

    ```json
    {
        "message": "User not found"
    }
    ```

  - **Code:** 404

    ```json
    {
        "message": "Book with ID 123 not found in your library"
    }
    ```

### Update Status

**Route:** `/api/update-status/<book_id>`

- **Method:** PUT
- **Purpose:** Updates the reading status of a specific book in the user's
  library.
- **URL Parameters:**
  - `book_id` (required): The ID of the book to update
- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
     {
      "message": "The status of 'The Great Gatsby' has been updated to 'Reading'.",
      "book": {
          "id": 1,
          "title": "The Great Gatsby",
          "author": "F. Scott Fitzgerald",
          "isbn": "9780743273565",
          "status": "Reading"
      }
    }


    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
    "message": "Invalid reading status provided 'Reaad'"
    }

    ```

  - **Code:** 404

    ```json
    {
        "message": "Book with ID -1000 not found in your library"
    }
    ```

  - **Code:** 500

    ```json
    {
        "message": "Error updating book status"
    }
    ```

## Review Routes

### Get User Reviews

**Route:** `/api/get-reviews`

- **Method:** GET
- **Purpose:** Retrieves all reviews for books in a user's library organized by
  reading status
- **Query Parameters:**
  - `username` (required): The username of the library owner
- **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
        "username": "newuser123"
    }
    ```

- **Error Responses:**
  - **Code:** 404

    ```json
    {
        "message": "You have not reviewed any books yet"
    }
    ```

  ### Add Review

**Route:** `/api/add-review`

- **Method:** POST
- **Purpose:** Route to add a review to a book
- **Query Parameters:**
  - `username` (required): The username of the library owner
  - 'message' (required): Message of the review
  - 'book_id' (required): Book ID to assign the review to
  - **Response Format:** JSON
- **Success Response:**
  - **Code:** 200
  - **Content:**

    ```json
    {
      "message": "Review added for '{book_to_review.title}'",
      "review": "Custom Message"
    }
    ```

- **Error Responses:**
  - **Code:** 400

    ```json
    {
        "message": "Please provide a review"
    }
    ```

- **Code:** 404

  ```json
  {
      "message": "Book with ID not found"
  }
  ```

- **Code:** 402

  ```json
  {
      "message": "You have already reviewed this book"
  }
  ```
