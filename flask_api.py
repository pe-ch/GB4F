import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, Response
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
from bson import ObjectId, errors


load_dotenv(".env")

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
    "book_shelf: "1"
} 
'''
    #extract the book_shelf info, since this is independent of the API
    book_shelf = query_params.pop("book_shelf", -1)


    if not query_params:
        return jsonify({"error": "Request body must contain JSON data"}), 400

    # Use the extracted JSON as query parameters
    raw_data = fetch_books_data(query_params)
    # Convert to Dataframe
    API_books_df= json_to_dataframe(raw_data, book_shelf)


    if API_books_df.empty:
        return jsonify({"message": "No books found for this query"}), 404

    return jsonify(API_books_df.to_dict(orient="records"))


@app.route('/select_book', methods=['POST'])
def select_book_API():
    """Selects a book from the previous search results using selection_id.
    {"selection_id":1}
    
    """
    global API_books_df # Access global variable

    data = request.get_json()
    selection_id = data.get("selection_id")

    if API_books_df is None:
        return jsonify({"error": "No active book search found"}), 400

    selected_book = API_books_df[API_books_df["selection_id"] == selection_id]

    if selected_book.empty:
        return jsonify({"error": "Invalid selection_id"}), 404


    # Get MongoDB client (connected to Atlas)
    # Get MongoDB Atlas URI from .env
    mongo_uri = get_mongo_uri()

    # Save to mongodb
    place_book_in_mongo(selected_book, mongo_uri, db_name="test", collection_name="stored_books")  # 🔥 Insert into MongoDB

    

    # **Flush API_books_df after selection**
    API_books_df = None  

    return jsonify({"message": "Book selected successfully!"})


@app.route('/get_selected_books', methods=['GET'])
def get_selected_books():
    """Fetch all selected books from MongoDB and return as JSON."""
    mongo_uri = get_mongo_uri()
    df = import_from_mongo(mongo_uri)  # 🔥 Fetch from MongoDB
    
    return jsonify(df.to_dict(orient="records"))


@app.route('/select_books_to_remove', methods=['POST'])
def select_books_to_remove():

    query_params = request.get_json() #this accepts a dict in the API format
    '''
    {
    "intitle": "Python",
    "inauthor": "Guido",
    "isbn": "9781449355739"
    "book_shelf: "1"
    } 
        '''
    
    #extract the book_shelf info, since this is independent of the API
    book_shelf = query_params.pop("book_shelf", -1)

    if not query_params:
        return jsonify({"error": "Request body must contain JSON data"}), 400

    query_params_uni= unify_json_inX_to_X(query_params)

    mongo_uri=get_mongo_uri()

    selected_books = or_filter_mongo(query_params_uni, mongo_uri=get_mongo_uri(), db_name="test", collection_name="stored_books")

    print(selected_books)
    return selected_books

@app.route('/remove_by_ID', methods=['POST'])
def remove_by_ID():
    data = request.get_json()
    
    
    mongo_ID = data.get("_id")
    mongo_ID = check_correct_mongo_ID(mongo_ID)
    print(mongo_ID)
    if mongo_ID is None:
        return jsonify({"message":"Wrong ID, nothing happened!"})


    mongo_uri=get_mongo_uri()
    book_removed = remove_selection_from_mongo(mongo_ID, mongo_uri, db_name="test", collection_name="stored_books")
    if book_removed:
        return jsonify({"message":"Book_removed"})
    
    return jsonify({"message":"Wrong ID, nothing happened!"})

    


    


if __name__ == '__main__':
    app.run(debug=True)
