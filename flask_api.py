import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, g
import requests
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import pandas as pd
import numpy as np
from IPython.display import Image, display
from functions_flask import *
import sqlite3


app = Flask(__name__)

# Sample Book Database (Initial)
df_books = pd.DataFrame([
    {"id": 1, "title": "Book A", "author": "Author X", "genre": "Fiction", "price": 12.99},
    {"id": 2, "title": "Book B", "author": "Author Y", "genre": "Science", "price": 19.99},
    {"id": 3, "title": "Book C", "author": "Author Z", "genre": "History", "price": 15.50},
])

# Internal database where chosen books are stored
df_selected_books = pd.DataFrame(columns=df_books.columns)

@app.route('/')
def home():
    return "Welcome to the Book API! Use /search_books, /select_book, and /get_selected_books."

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/search_books', methods=['POST'])
def search_books():
    """Receives a JSON query and fetches matching books from Google Books API."""
    global API_books_df  # Declare it as global
    
    query_params = request.get_json() #this accepts a dict in the API format
    '''
    {
    "intitle": "Python",
    "inauthor": "Guido",
    "isbn": "9781449355739"
} 
'''

    if not query_params:
        return jsonify({"error": "Request body must contain JSON data"}), 400

    # Use the extracted JSON as query parameters
    raw_data = fetch_books_data(query_params)
    # Convert to Dataframe
    API_books_df= json_to_dataframe(raw_data)

    # Filter books based on the query
    #filtered_books = df_books[df_books["genre"].str.contains(query, case=False, na=False)]

    if API_books_df.empty:
        return jsonify({"message": "No books found for this query"}), 404

    return jsonify(API_books_df.to_dict(orient="records"))

#stored_books_df = pd.DataFrame()  # Global DataFrame for storing selected books

@app.route('/select_book', methods=['POST'])
def select_book_API():
    """Selects a book from the previous search results using book_id."""
    global API_books_df # Access global variable

    data = request.get_json()
    book_id = data.get("book_id")

    if API_books_df is None:
        return jsonify({"error": "No active book search found"}), 400

    selected_book = API_books_df[API_books_df["book_id"] == book_id]

    if selected_book.empty:
        return jsonify({"error": "Invalid book_id"}), 404

    # Save to SQLite
    with sqlite3.connect("books.db") as conn:
        selected_book.to_sql("stored_books", conn, if_exists="append", index=False)

    # Append to stored books
    #stored_books_df = pd.concat([stored_books_df, selected_book], ignore_index=True)

    # **Flush API_books_df after selection**
    API_books_df = None  

    return jsonify({"message": "Book selected successfully!"})


@app.route('/get_selected_books', methods=['GET'])
def get_selected_books():
    """Fetch all selected books from the SQLite database."""
    with sqlite3.connect("books.db") as conn:
        df = pd.read_sql("SELECT * FROM stored_books", conn)

    return jsonify(df.to_dict(orient="records"))

if __name__ == '__main__':
    app.run(debug=True)
