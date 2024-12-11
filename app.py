from flask import Flask, jsonify, request
from models.user_model import (
    User,
    get_library,
    add_book_personal_library,
    delete_book_from_library,
    update_status,
    add_book_review,
    delete_review,
    get_reviews,
    add_book_favorite_books,

)

app = Flask(__name__)


@app.route("/")
def home():
    return {"message": "Library API is running"}


# Health Check Route


@app.route("/api/health", methods=["GET"])
def healthcheck():
    """
    Health check route to verify the service is running.

    Returns:
        JSON response indicating the health status of the service.
    """
    app.logger.info("Health check")
    return jsonify({"status": "healthy"}, 200)


# Authentication Routes


@app.route("/create-account", methods=["POST"])
def create_account():
    """Create a new user account with salted password hash.

    Args:
        None directly. Expects a JSON request body with:
            username (str): The desired username for the new account
            password (str): The password for the new account

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with a message indicating success or failure
            - status_code: HTTP status code
                200: Success
                400: Bad request (missing/invalid data)
                500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify({"message": "Please provide both username and password"}),
                400,
            )

        return User.create_user_account(username=username, password=password)
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    """Authenticate user credentials and create a session.

    Args:
        None directly. Expects a JSON request body with:
            username (str): The username for authentication
            password (str): The password for authentication

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with a welcome message or error
            - status_code: HTTP status code
                200: Success (valid credentials)
                400: Bad request (missing credentials)
                401: Unauthorized (invalid credentials)
    """
    data = request.get_json()

    if not data.get("username") or not data.get("password"):
        return jsonify({"message": "Please provide both username and password"}), 400

    user = User.get_user_by_username(data["username"])

    if user and user.check_password(data["password"]):
        return jsonify({"message": f"Welcome back, {user.username}!"})

    return jsonify({"message": "Invalid username or password"}), 401


@app.route("/update-password", methods=["PUT"])
def update_password():
    """Update user's password with new salt and hash.

    Args:
        None directly. Expects a JSON request body with:
            username (str): The username of the account
            old_password (str): The current password for verification
            new_password (str): The new password to set

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with a message indicating success or failure
            - status_code: HTTP status code
                200: Success (password updated)
                400: Bad request (missing credentials)
                401: Unauthorized (invalid credentials)
                500: Server error
    """
    data = request.get_json()

    if not all(k in data for k in ["username", "old_password", "new_password"]):
        return (
            jsonify(
                {"message": "Please provide username, old_password, and new_password"}
            ),
            400,
        )

    user = User.get_user_by_username(data["username"])

    if not user or not user.check_password(data["old_password"]):
        return jsonify({"message": "Invalid username or password"}), 401

    return user.update_password(data["new_password"])


@app.route("/delete-account", methods=["DELETE"])
def delete_account():
    """Delete a user account and all associated data.

    Args:
        None directly. Expects a JSON request body with:
            username (str): The username of the account
            password (str): The password of the account

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with success or error message
            - status_code: HTTP status code
                200: Success (account deleted)
                404: Not found (user doesn't exist)
                500: Server error (database error)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), 400

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify({"message": "Please provide both username and password"}),
                400,
            )

        user = User.get_user_by_username(username)
        if not user:
            return jsonify({"message": "User not found"}), 404

        if not user.check_password(password):
            return jsonify({"message": "Invalid password"}), 401

        # Delete user's data
        return User.delete_user_account(username)

    except Exception as e:
        return jsonify({"message": str(e)}), 500


# Library Routes


@app.route("/api/get-library", methods=["GET"])
def get_user_library():
    """Get the user's library with books organized by status.

    Args:
        None directly. Expects a query parameter with:
            username (str): The username of the account

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with the user's library
            - status_code: HTTP status code
                200: Success
                400: Bad request (missing/invalid data)
                404: Not found (user not found)
    """
    username = request.args.get("username")
    if not username:
        return jsonify({"message": "Please provide a username"}), 400

    user = User.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return get_library(user)


@app.route("/api/add-book", methods=["POST"])
def add_book():
    """Add a book to the user's library using OpenLibrary API.

    Args:
        None directly. Expects a JSON request body with:
            username (str): The username of the account
            title (str): The title of the book to add
            author (str): The author of the book to add
            status (str): The status of the book to add (Want to Read, Reading, Read)

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with a message indicating success or failure
            - status_code: HTTP status code
    """
    data = request.get_json()

    if not data.get("username"):
        return jsonify({"message": "Please provide a username"}), 400

    if not data.get("title"):
        return jsonify({"message": "Please provide a book title"}), 400

    user = User.get_user_by_username(data["username"])
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Remove username from data before passing to add_book_personal_library
    book_data = {k: v for k, v in data.items() if k != "username"}
    return add_book_personal_library(user, book_data)


@app.route("/api/add-review", methods=["POST"])
def add_review():
    """
    Route to add a review to a book.

    Returns:
        JSON response indicating the review has been added.
    Raises:
        404 error if there is an issue with the database.
    """
    app.logger.info("Adding review")
    data = request.get_json()
    if not data.get("username"):
        return jsonify({"message": "Please provide a username"}), 400

    if not data.get("title"):
        return jsonify({"message": "Please provide a book title"}), 400

    if not data.get("review"):
        return jsonify({"message": "Please provide a review"}), 400

    if not data.get("book_id"):
        return jsonify({"message": "Please provide a book ID"}), 400

    user = User.get_user_by_username(data["username"])
    if not user:
        return jsonify({"message": "User not found"}), 404

    book_id = data["book_id"]
    review = data["review"]

    return add_book_review(user, review, book_id)


@app.route("/api/get-reviews", methods=["GET"])
def get_user_reviews():
    """
    Route to get reviews all reviews by a user.

    Returns:
        JSON response with reviews from a user.
    Raises:
        404 error if there is an issue with the database.
    """
    app.logger.info("Getting reviews")
    username = request.args.get("username")
    if not username:
        return jsonify({"message": "Please provide a username"}), 400

    user = User.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return get_reviews(user)


@app.route("/api/delete-review", methods=["DELETE"])
def delete_user_review():
    """
    Route to delete a review from a user.

    Returns:
        JSON response indicating the review has been deleted.
    Raises:
        404 error if there is an issue with the database.
    """
    app.logger.info("Deleting review")
    data = request.get_json()
    if not data.get("username"):
        return jsonify({"message": "Please provide a username"}), 400

    if not data.get("book_id"):
        return jsonify({"message": "Please provide a book ID"}), 400

    user = User.get_user_by_username(data["username"])
    if not user:
        return jsonify({"message": "User not found"}), 404

    book_id = data["book_id"]

    return delete_review(user, book_id)


@app.route("/api/delete-book/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book from the user's library.

    Args:
        None directly. Expects a query parameter with:
            username (str): The username of the account

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with a message indicating success or failure
            - status_code: HTTP status code
    """
    username = request.args.get("username")
    if not username:
        return jsonify({"message": "Please provide a username"}), 400

    user = User.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return delete_book_from_library(user, book_id)


@app.route("/api/update-status/<int:book_id>", methods=["PUT"])
def update_book_status(book_id):
    """Update a book's reading status.

    Args:
        None directly. Expects a JSON request body with:
            username (str): The username of the account
            new_status (str): The new status of the book (Want to Read, Reading, Read)

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with a message indicating success or failure
            - status_code: HTTP status code
    """
    data = request.get_json()
    username = data.get("username")
    new_status = data.get("status")

    if not username:
        return jsonify({"message": "Please provide a username"}), 400

    if not new_status:
        return jsonify({"message": "Please provide a new status"}), 400

    if new_status not in ["Want to Read", "Reading", "Read"]:
        return (
            jsonify({"message": "Status must be: Want to Read, Reading, or Read"}),
            400,
        )

    user = User.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return update_status(user, book_id, new_status)


@app.route("/api/add-favorite-book", methods=["POST"])
def add_favorite_book():
    """Add a book to a user's favorite books library.

    Args:
        None directly. Expects a JSON request body with:
            username (str): The username of the account
            book_id (int): The ID of the book to add to favorites

    Returns:
        tuple: A tuple containing (response, status_code) where:
            - response: JSON object with a message indicating success or failure
            - status_code: HTTP status code
                200: Success (book added to favorites)
                400: Bad request (missing/invalid data)
                404: Not found (user or book not found)
    """
    data = request.get_json()

    if not data.get("username"):
        return jsonify({"message": "Please provide a username"}), 400

    if not data.get("book_id"):
        return jsonify({"message": "Please provide a book ID"}), 400

    username = data["username"]
    book_id = data["book_id"]

    user = User.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    user_library = get_library(user)
    if not any(book["id"] == book_id for book in user_library["books"]):
        return jsonify({"message": "Book not found in user's personal library"}), 404

    # Add the book to the favorite books table (assuming there is a favorite_books table)
    return add_book_favorite_books(user, book_id)



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
