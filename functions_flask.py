import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
import requests
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import pandas as pd
import numpy as np
from IPython.display import Image, display


def fetch_books_data(query_params):
    """
    Fetch raw data from the Google Books API with flexible query parameters.

    :param query_params: A dictionary of query parameters (e.g., {"intitle": "Python", "inauthor": "Guido"}).
    :return: The raw JSON response from the API.
    """
    # Define the base URL for the Google Books API
    url = "https://www.googleapis.com/books/v1/volumes"

    # Dynamically build the query string from the dictionary of query parameters
    # Each key-value pair in the dictionary is formatted as "key:value"
    # The "join" function combines these pairs with spaces to create the full query string
    query = " ".join(f"{key}:{value}" for key, value in query_params.items())

    # Define the parameters for the API request
    params = {
        "q": query,  # The query string constructed above
        "maxResults": 5,  # Limit the number of results returned by the API to x
        "printType": "books",
        "langRestrict": "de"
    }

    try:
        # Send a GET request to the Google Books API with the specified parameters
        response = requests.get(url, params=params)

        # Check for HTTP errors; raise an exception if the response status indicates an error
        response.raise_for_status()

        # If the request is successful, return the JSON data from the API response
        return response.json()

    except requests.exceptions.RequestException as e:
        # If an error occurs during the request, print the error message
        print(f"API request error: {e}")

        # Return an empty dictionary to signify failure
        return {}

def format_json(raw_data):
    """
    Format and pretty-print JSON data.

    :param data: The JSON data (as a Python dictionary).
    :return: A formatted string representation of the JSON data.
    """
    try:
        # Convert JSON data to a pretty-printed string
        return json.dumps(raw_data, indent=4)
    except (TypeError, ValueError) as e:
        # Handle errors in case the input is not valid JSON
        print(f"Error formatting JSON: {e}")
        return "{}"

def json_to_dataframe(raw_data):
    """
    Transform JSON data from the Google Books API into a pandas DataFrame.

    :param json_data: Raw JSON data from the Google Books API.
    :return: A pandas DataFrame containing relevant book information.
    """
    try:
        # Extract the list of books from the JSON data
        items = raw_data.get("items", [])

        # Prepare a list to store extracted metadata
        metadata = []

        # Initialize book_id counter
        book_id_counter = 1

        # Iterate through the books and extract relevant fields
        for item in items:
            volume_info = item.get("volumeInfo", {})
            record = {
                "book_id": book_id_counter,  # Add running book_id
                "ID": item.get("id", np.nan),
                "Title": volume_info.get("title", np.nan),
                "Authors": ", ".join(volume_info.get("authors", [])) if "authors" in volume_info else np.nan, #note this may return an emtpy [] not NAN
                "Publisher": volume_info.get("publisher", np.nan),
                "Page Count": volume_info.get("pageCount", np.nan),
                "Language": volume_info.get("language", np.nan),
                "Category": ", ".join(volume_info.get("categories", [])) if "categories" in volume_info else np.nan, #note this may return an emtpy [] not NAN
                "Thumbnail": volume_info.get("imageLinks", {}).get("thumbnail", np.nan), #note this may return an emtpy {} not NAN


                "ISBN_13": next(
                    (
                        identifier["identifier"]
                        for identifier in volume_info.get("industryIdentifiers", [])
                        if identifier["type"] == "ISBN_13"
                    ),
                    np.nan,
                ),
                "ISBN_10": next(
                    (
                        identifier["identifier"]
                        for identifier in volume_info.get("industryIdentifiers", [])
                        if identifier["type"] == "ISBN_10"
                    ),
                    np.nan,
                ),
            }
            metadata.append(record)

            # Increment the book_id counter after each book
            book_id_counter += 1

        # Create a DataFrame from the metadata
        return pd.DataFrame(metadata)

    except Exception as e:
        print(f"Error processing JSON data: {e}")
        return pd.DataFrame()

def initiate_stored_books_df():
    global stored_books_df

    # Check if 'stored_books_df' exists or is None
    if "stored_books_df" not in globals() or stored_books_df is None:
        stored_books_df = pd.DataFrame()  # Instantiate an empty DataFrame

    # Add 'Is_Placed' column if DataFrame is empty
    if stored_books_df.empty:
        stored_books_df = pd.DataFrame({
            "Title": [np.nan],
            "Authors": [np.nan],
            "ISBN_10": [np.nan],
            "Is_Placed": [False]
        })

def and_filter(stored_books_df, and_query):
    #accepts a dictionary
    #clean search parameter
    and_query = {key: str(value).strip() for key, value in and_query.items()}
    and_query = {key:  f".*{value}.*" for key, value in and_query.items()}
    # Start with a filter that includes all rows

    mask = pd.Series(True, index=stored_books_df.index)

    # Apply each filter in the dictionary
    for key, value in and_query.items():
       mask &= stored_books_df[key].fillna("").str.contains(value, regex=True, na=False)  # Combine conditions with AND

    filt_df= stored_books_df.loc[mask]
    return filt_df

def or_filter(stored_books_df, or_query):
    #accepts a dictionary
    #clean search parameter
    or_query = {key: str(value).strip() for key, value in or_query.items()}
    or_query = {key:  f".*{value}.*" for key, value in or_query.items()}
    # Start with a filter that includes all rows

    mask = pd.Series(False, index=stored_books_df.index)

    # Apply each filter in the dictionary
    for key, value in or_query.items():
        mask |= stored_books_df[key].fillna("").str.contains(value, regex=True, na=False)  # Combine conditions with OR

    filt_df= stored_books_df.loc[mask]
    return filt_df

def place_selection(selection_df):
    """
    Place a selection into the global stored_books_df, ensuring no duplicates are added.
    If 'stored_books_df' does not exist or is None, it initializes it as an empty DataFrame.

    Args:
    - selection_df (pd.DataFrame): A single-row DataFrame to be added to stored_books_df.

    Returns:
    - None: Updates the global stored_books_df.
    """
    global stored_books_df  # Access the global variable

    # Check if 'stored_books_df' exists or is None
    if "stored_books_df" not in globals() or stored_books_df is None:
        stored_books_df = pd.DataFrame()  # Instantiate an empty DataFrame

    if selection_df is None:
        return None

    selection_df["Is_Placed"]= True
    all_but_IP = selection_df.columns.difference(['Is_Placed'])
    stored_books_df = pd.concat([stored_books_df, selection_df]).drop_duplicates(subset=all_but_IP, ignore_index=True, keep="last") #this drops a book which was Placed but set to removed this is not elegant but ok for now

    print("Updated stored_books_df:")
    display(stored_books_df.head(5))

def select_book_from_internal_database(stored_books_df, and_query, or_query):
    """
    Allows the user to select a book from the results in the DataFrame,
    displaying them in batches of x <-- can be defined.

    find_query is a dictionary containing any number of pairs like Author:Michael...
    find_query = {'Author': 'Michael'}
    """
    display(Image(url= "http://books.google.com/books/content?id=JfP8csMrHBUC&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api"))

    # Check if the DataFrame is empty
    if stored_books_df.empty:
        print("No books available to select.")
        return None  # Can be enhanced by asking to repeat

    start_index = 0  # Initial starting index for displaying books
    books2display = 4  # Adjusted to show x books per batch


    #define search parameter
    # Start with a filter that includes all rows
    if or_query:
        or_books_df= or_filter(stored_books_df, or_query)
    else:
        or_books_df=pd.DataFrame()

    if and_query:
        and_books_df = and_filter(stored_books_df, and_query)
    else:
        and_books_df=pd.DataFrame()

    books_df=pd.DataFrame()

    books_df = pd.concat([and_books_df, or_books_df]).drop_duplicates(ignore_index=False) #False to retain the index

    Placed_books = books_df.loc[books_df["Is_Placed"] == True]  # IMPORTANT This restricts the search to books which have not been removed!

    print(f"There were {len(books_df)} books found")
    while True:
        # Calculate end_index based on the start_index and books2display
        end_index = start_index + books2display

        subset_books = Placed_books.iloc[start_index:end_index]

        if subset_books.empty:
            print("No more books to display.")
            return None  # Stop if there are no more books to display

        print("\nAvailable books:")
        j=0
        for i, row in subset_books.iterrows():
            j+=1
            print(f"{j}: {row['Title']} by {row['Authors']}")


            # Validate thumbnail URL
            thumbnail_url = row.get('Thumbnail', None)
            if pd.notna(thumbnail_url) and isinstance(thumbnail_url, str):
                try:
                    display(Image(url=thumbnail_url))
                except Exception as e:
                    print(f"Error displaying image: {e}")
            else:
                print("Thumbnail not available or invalid URL")




        # Show option to display more books only if there are more books to show
        if int(len(subset_books)) % int(books2display) == 0:
            print(f"{int(books2display) +1}: Show the next {int(books2display)} books") #only is shown when there are books to show

        print("0: Cancel selection")

        # Prompt the user to choose a book
        try:
            choice = int(input(f"\nEnter the number of the book you want to select, {books2display + 1} to show more, or 0 to cancel: "))

            if 1 <= choice <= len(subset_books):
                # Return the selected book's data as a df
                selected_book = subset_books.iloc[[choice - 1]]  # Use .to_dict() to return a dict [[]] returns a df
                print(f"\nYou selected: {selected_book['Title']} by {selected_book['Authors']}")
                return selected_book
            elif choice == (books2display + 1):
                # Show the next batch of books
                start_index += books2display
            elif choice == 0:
                print("Selection canceled.")
                return None
            else:
                print("Invalid selection. Please choose a valid option.")
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 6, or 0 to cancel.")

def flush_stored_books_df():
    really = input("Do you want to empty the internal book storage??? then say: yes ")
    if really == "yes":
        global stored_books_df  # Modify global variable
        stored_books_df = None  # Reset to empty DataFrame
        print("Internal book storage emptied.")
    else:
        print("Nothing happened...")

def remove_selection_by_index(selected_book):
    #This function changes to Is_Placed Lable to false on the selection

    if selected_book is None:
        selected_book= pd.DataFrame()
    global stored_books_df  # Access the global variable

    # Check if 'stored_books_df' exists or is None
    #if "stored_books_df" not in globals() or stored_books_df is None:
        #stored_books_df = pd.DataFrame()  # Instantiate an empty DataFrame


    print(selected_book.index)
    stored_books_df.loc[selected_book.index, "Is_Placed"] = False #Must be False

    print("Updated stored_books_df:")
    print(stored_books_df.head(5))

#This works but is less elegant

def remove_selection_by_drop_dublicates(selected_book):
    #This function changes to Is_Placed Lable to false on the selection
    if selected_book is None:
        selected_book = pd.DataFrame()
    if not selected_book.empty:
        global stored_books_df  # Access the global variable
        print("SB")
        print(stored_books_df)
        print("SelB")
        print(selected_book)
        selected_book["Is_Placed"]= False
        print("SelB_pla")
        print(selected_book)
        all_but_IP = selection_df.columns.difference(['Is_Placed'])
        stored_books_df = pd.concat([stored_books_df, selected_book]).drop_duplicates(subset=all_but_IP, ignore_index=True, keep="last")

        print("Updated stored_books_df:")
        print(stored_books_df.head(5))

def search_removed_books(query_params):

    # remap query_params
    original_query = query_params

# Mapping of old keys to new keys

    # Handle ISBN length dynamically and return a key mapping
    key_mapping = (lambda l: {
        "intitle": "Title",
        "inauthor": "Authors",
        "isbn": "ISBN_13" if l == 13 else "ISBN_10" if l == 10 else None
    })(len(query_params.get("isbn", "")))

    # Remove None values from key_mapping (if no ISBN length matches)
    key_mapping = {k: v for k, v in key_mapping.items() if v is not None}

    # Rename keys in the original dictionary
    renamed_query = {key_mapping.get(k, k): v for k, v in original_query.items()}

    global stored_books_df

        # Check if 'stored_books_df' exists or is None
    if "stored_books_df" not in globals() or stored_books_df is None:
        stored_books_df = pd.DataFrame()  # Instantiate an empty DataFrame



    or_query = renamed_query # this just uses the or query for now

    if renamed_query and not stored_books_df.empty:
        or_books_df= or_filter(stored_books_df, or_query)
    else:
        or_books_df=pd.DataFrame()
        return or_books_df

    books_df = or_books_df  # this is until the AND OR function is implemented here as well
    Removed_books = books_df.loc[books_df["Is_Placed"] == False]   #This restricts the search to books which has been removed!

    return Removed_books

    #if and_query:
    #    and_books_df = and_filter(stored_books_df, and_query)
    #else:
    #    and_books_df=pd.DataFrame()

def select_book_from_results(API_books_df, removed_books_df):
    """
    Allows the user to select a book from the results in the DataFrame,
    displaying them in batches of x <-- can be defined.

    :param books_df: Pandas DataFrame containing book data.
    :return: A df of the selected book's metadata or None if no valid selection is made.
    """

    #API_books_df is the input from the API search
    #removed_books_df is a search with the same parameters in the internal database
    # Ensure 'Is_Placed' column exists


    all_but_IP = removed_books_df.columns.difference(['Is_Placed'])

    books_df = pd.concat([removed_books_df, API_books_df]).drop_duplicates(subset=all_but_IP, ignore_index=True, keep="first")


    books_df= API_books_df



    # Check if the DataFrame is empty
    if books_df.empty:
        print("No books available to select.")
        return None  # Can be enhanced by asking to repeat

    start_index = 0  # Initial starting index for displaying books
    books2display = 4  # Adjusted to show x books per batch
    print(f"There were {len(books_df)} books found")

    while True:
        # Calculate end_index based on the start_index and books2display
        end_index = start_index + books2display
        subset_books = books_df.iloc[start_index:end_index]

        if subset_books.empty:
            print("No more books to display.")
            return None  # Stop if there are no more books to display

        print("\nAvailable books:")
        j=0
        for i, row in subset_books.iterrows():
            j+=1
            print(f"{j}: {row['Title']} by {row['Authors']}")

            # Validate thumbnail URL
            thumbnail_url = row.get('Thumbnail', None)
            if pd.notna(thumbnail_url) and isinstance(thumbnail_url, str):
                try:
                    display(Image(url=thumbnail_url))
                except Exception as e:
                    print(f"Error displaying image: {e}")
            else:
                print("Thumbnail not available or invalid URL")



        # Show option to display more books only if there are more books to show
        if int(len(subset_books)) % int(books2display) == 0:
            print(f"{int(books2display) +1}: Show the next {int(books2display)} books") #only is shown when there are books to show

        print("0: Cancel selection")

        # Prompt the user to choose a book
        try:
            choice = int(input(f"\nEnter the number of the book you want to select, {books2display + 1} to show more, or 0 to cancel: "))

            if 1 <= choice <= len(subset_books):
                # Return the selected book's data as a df
                selected_book = subset_books.iloc[[choice - 1]]  # Use .to_dict() to return a dict [[]] returns a df
                print(f"\nYou selected: {selected_book['Title']} by {selected_book['Authors']}")
                return selected_book
            elif choice == (books2display + 1):
                # Show the next batch of books
                start_index += books2display
            elif choice == 0:
                print("Selection canceled.")
                return None
            else:
                print("Invalid selection. Please choose a valid option.")
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 6, or 0 to cancel.")