from flask import Flask
from models.user_model import User

app = Flask(__name__)


@app.route("/")
def home():
    return {"message": "Library API is running"}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
