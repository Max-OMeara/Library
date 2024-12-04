import logging
from typing import List
# other imports - perhaps to utils

class User:
  id: int
  username: string
  password: string
  personal_library = [] # list of JSON blobs/python dictionary
  favorite_books = [] # list of JSON blobs/python dictionaries
#end class

def create_user_account(username: str, password: str):
  try:
    # need to figure out how to get a unique ID number
      with get_db_connection() as conn:
          cursor = conn.cursor()
          cursor.execute("""
              INSERT INTO users (username, password, [], [])
              VALUES (?, ?, ?, ?, ?)
          """, (username, password, [], []))
          conn.commit()
          logger.info("User successfully added to the database: %s", username)
  except sqlite3.IntegrityError:
      logger.error("Duplicate user: %s", username)
      raise ValueError(f"User with username '{username}' already exists")
  except sqlite3.Error as e:
      logger.error("Database error: %s", str(e))
      raise e
  #end except
#enddef

def update_password(user, password):
  """Updates a user's password
  Arguments
  user: class User
  password: string, new password
  IDK IF WE NEED TO CHANGE THE DATABASE OR JUST THE CLASS ATTRIBUTE"""
  
  user.password = password
  try:
      with get_db_connection() as conn:
          cursor = conn.cursor()
          cursor.execute("""
              INSERT INTO meals (meal, cuisine, price, difficulty)
              VALUES (?, ?, ?, ?)
          """, (meal, cuisine, price, difficulty))
          conn.commit()
          logger.info("Password successfully changed for user: %s", user.username)

  except sqlite3.IntegrityError:
      logger.error("Error updating password for user: %s", user.username)
      raise ValueError(f"Error updating password for user'{user.username}")
#enddef

def add_review(user, review, book):
  """Adding a user's review of a particular book
  Arguments
  user: class User
  review: string, review to be added
  book: string???"""
#enddef

def delete_review(user, book):
  """Deleting a user's review of a given book
  Arguments
  user: class User
  book: string????
  Raises
  ??? ValueError"""
#enddef


def add_book_personal_library()
def add_book_favorite_books()

def get_library(user):
  """Prints out a user's personal library
  Arguments
  user: class User"""
  print(user.personal_library)
#enddef

def get_favorite_books(user):
  """Prints out a user's favorite books
  Arguments
  user: class User"""
  print(user.favorite_books)
#enddef
