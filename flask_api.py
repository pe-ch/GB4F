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
import sqlite3
import os
from dotenv import load_dotenv

app = Flask(__name__)

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


    if API_books_df.empty:
        return jsonify({"message": "No books found for this query"}), 404

    return jsonify(API_books_df.to_dict(orient="records"))


@app.route('/select_book', methods=['POST'])
def select_book_API():
    """Selects a book from the previous search results using book_id.
    {"book_id":1}
    
    """
    global API_books_df # Access global variable

    data = request.get_json()
    book_id = data.get("book_id")

    if API_books_df is None:
        return jsonify({"error": "No active book search found"}), 400

    selected_book = API_books_df[API_books_df["book_id"] == book_id]

    if selected_book.empty:
        return jsonify({"error": "Invalid book_id"}), 404


    # Get MongoDB client (connected to Atlas)
    # Get MongoDB Atlas URI from .env
    mongo_uri = get_mongo_uri()

    # Save to mongodb
    place_book_in_mongo(selected_book, mongo_uri)  # 🔥 Insert into MongoDB

    # **Flush API_books_df after selection**
    API_books_df = None  

    return jsonify({"message": "Book selected successfully!"})


@app.route('/get_selected_books', methods=['GET'])
def get_selected_books():
    """Fetch all selected books from MongoDB and return as JSON."""
    mongo_uri = get_mongo_uri()
    df = import_from_mongo(mongo_uri)  # 🔥 Fetch from MongoDB

    return jsonify(df.to_dict(orient="records"))


if __name__ == '__main__':
    app.run(debug=True)
