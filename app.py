from flask import Flask, jsonify, request
from models.user_model import (
    User,
    get_library,
    add_book_personal_library,
    delete_book_from_library,
)

app = Flask(__name__)


@app.route("/")
def home():
    return {"message": "Library API is running"}


# Authentication Routes


@app.route("/create-account", methods=["POST"])
def create_account():
    """Create a new user account with salted password hash"""
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
    """Verify user credentials using hashed password"""
    data = request.get_json()

    if not data.get("username") or not data.get("password"):
        return jsonify({"message": "Please provide both username and password"}), 400

    user = User.get_user_by_username(data["username"])

    if user and user.check_password(data["password"]):
        return jsonify({"message": f"Welcome back, {user.username}!"})

    return jsonify({"message": "Invalid username or password"}), 401


@app.route("/update-password", methods=["PUT"])
def update_password():
    """Update user password with new salt and hash"""
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


# Library Routes


@app.route("/api/get-library", methods=["GET"])
def get_user_library():
    """Get the user's library with books organized by status"""
    username = request.args.get("username")
    if not username:
        return jsonify({"message": "Please provide a username"}), 400

    user = User.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return get_library(user)


@app.route("/api/add-book", methods=["POST"])
def add_book():
    """Add a book to the user's library using OpenLibrary API"""
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

    user = User.get_user_by_username(data["username"])
    if not user:
        return jsonify({"message": "User not found"}), 404

    book_data = {k: v for k, v in data.items() if k != "username"}

    return add_review(user, book_data)

@app.route("/api/get-reviews", methods=["GET"])
def get_reviews():
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

@app.route("/api/delete-book/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    """Delete a book from the user's library"""
    username = request.args.get("username")
    if not username:
        return jsonify({"message": "Please provide a username"}), 400

    user = User.get_user_by_username(username)
    if not user:
        return jsonify({"message": "User not found"}), 404

    return delete_book_from_library(user, book_id)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
