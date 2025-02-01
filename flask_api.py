import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
import requests
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import pandas as pd
import numpy as np
from IPython.display import Image, display
from functions_flask import *

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

@app.route('/select_book', methods=['POST'])
def select_book():
    """Receives selected book and adds it to internal database."""
    global df_selected_books  # Use global to modify DataFrame

    data = request.get_json()

    if not data or "id" not in data:
        return jsonify({"error": "Missing 'id' in request"}), 400

    book_id = data["book_id"]
    
    # Find the book by ID
    selected_book = df_books[df_books["book_id"] == book_id]

    if selected_book.empty:
        return jsonify({"error": "Book not found"}), 404

    # Append to internal database
    df_selected_books = pd.concat([df_selected_books, selected_book], ignore_index=True)

    return jsonify({"message": f"Book {book_id} added successfully"}), 200

@app.route('/get_selected_books', methods=['GET'])
def get_selected_books():
    """Returns all books that were selected."""
    return jsonify(df_selected_books.to_dict(orient="records"))

if __name__ == '__main__':
    app.run(debug=True)
