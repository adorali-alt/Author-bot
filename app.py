import math
import os
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat

from flask import Flask
import requests
import json
import random
import time

from flask import (
    Blueprint, flash, render_template, request
)

bp = Blueprint('generate', __name__, url_prefix='/')

GUT_URL_TEMPLATE = "http://gutendex.com/books?search="

END_TOKEN = "***END***"


def create_app(test_config=None):
    # create and configure the app
    # creates Flask instance
    app = Flask(__name__, instance_relative_config=True)
    # override SECRET_KEY with random
    app.config.from_mapping(
        SECRET_KEY='dev',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.register_blueprint(bp)
    app.add_url_rule('/', endpoint='empty')

    return app


class Dictogram(dict):
    def __init__(self, iterable=None):
        """Initialize this histogram as a new dict; update with given items"""
        super(Dictogram, self).__init__()
        self.types = 0  # the number of distinct item types in this histogram
        self.tokens = 0  # the total count of all item tokens in this histogram
        if iterable:
            self.update(iterable)

    def update(self, iterable):
        """Update this histogram with the items in the given iterable"""
        for item in iterable:
            if item in self:
                self[item] += 1
                self.tokens += 1
            else:
                self[item] = 1
                self.types += 1
                self.tokens += 1

    def count(self, item):
        """Return the count of the given item in this histogram, or 0"""
        if item in self:
            return self[item]
        return 0

    def return_random_word(self):
        # Another way:  Should test: random.choice(histogram.keys())
        random_key = random.sample(self, 1)
        return random_key[0]

    def return_weighted_random_word(self):
        # Step 1: Generate random number between 0 and total count - 1
        random_int = random.randint(0, self.tokens - 1)
        index = 0
        list_of_keys = list(self.keys())
        # print 'the random index is:', random_int
        for i in range(0, self.types):
            index += self[list_of_keys[i]]
            # print index
            if index > random_int:
                # print list_of_keys[i]
                return list_of_keys[i],


# FILE 2

def token_ends_sentence(token):
    has_punctuation = token.endswith(".") or token.endswith("!") or token.endswith("?")
    is_a_title = token == "Mr." or token == "Mrs." or token == "Ms." or token == "Dr." or token == "St."
    return has_punctuation and (not is_a_title)


def load_higher_order_markov_model(markov_model, order, data):
    for i in range(0, len(data) - order):
        # Check for end tokens to add
        for j in range(i, i + order):
            if token_ends_sentence(data[j]):
                data.insert(j + 1, END_TOKEN)
        # Create the window
        window = tuple(data[i: i + order])
        # Add to the dictionary
        if window in markov_model:
            # We have to just append to the existing Dictogram
            markov_model[window].update([data[i + order]])
        else:
            markov_model[window] = Dictogram([data[i + order]])


def generate_random_start(model):
    # Valid starting words are words that started a sentence in the corpus
    if (END_TOKEN,) in model:
        seed_word = (END_TOKEN,)
        while seed_word == (END_TOKEN,):
            seed_word = model[(END_TOKEN,)].return_weighted_random_word()
        return ''.join(seed_word)
    else:
        seed_word = random.sample(model.keys(), 1)
        return seed_word[0]


def generate_random_sentence(model):
    curr_word = (generate_random_start(model),)
    sentence = []

    while curr_word != (END_TOKEN,):
        sentence.append(''.join(curr_word) + " ")
        curr_word = model[curr_word].return_weighted_random_word()
    return ''.join(sentence)


def generate_random_paragraph(model):
    sentence = ""
    for i in range(0, 5):
        sentence += generate_random_sentence(model)
    return sentence


# FILE 3


def find_text(book, query_name):
    # check author
    query_names = query_name.split()
    # assume its invalid
    is_written_by_any_author = False

    # check author
    for actual_author in book["authors"]:
        actual_author_name = actual_author["name"].lower()
        # assume this author wrote it
        is_written_by_this_author = True
        for part in query_names:
            # falses bubble up
            is_written_by_this_author = is_written_by_this_author and (part in actual_author_name)
        # trues bubble up
        is_written_by_any_author = is_written_by_any_author or is_written_by_this_author

    # check language
    is_in_english = "en" in book["languages"]

    if is_written_by_any_author and is_in_english and (book['media_type'] == "Text"):
        url = 'dummy'
        if 'text/plain' in book['formats']:
            url = book['formats']["text/plain"]
        elif 'text/plain; charset=utf-8' in book['formats']:
            url = book['formats']['text/plain; charset=utf-8']

        if url.endswith('.txt'):
            response = requests.get(url).content.decode("utf-8", "ignore")
            return response


def chunk_up_text(raw_text):
    sliced_raw_text = []
    raw_text_tokens = raw_text.split()
    step = math.floor(len(raw_text_tokens) / 50)
    for i in range(50):
        print(i)
        start_index = step * i
        end_index = min(start_index + step, len(raw_text_tokens))
        print(start_index, end_index)
        sliced_raw_text.append(raw_text_tokens[start_index:end_index])

    return sliced_raw_text


@bp.route('/submit', methods=('GET', 'POST'))
def empty():
    author_name = "Author"
    speech = "..."

    # if they submitted their author:
    if request.method == 'POST':
        # replace spaces with url encoded version
        author_name = request.form['name']
        query = author_name.lower().replace(' ', '%20')
        # fetch book list
        try:
            start_time = time.time()
            response = requests.get(GUT_URL_TEMPLATE + query).content
            end_time = time.time()
            print('timed operation : get from gutendex : {}'.format(end_time - start_time))

            # return all valid books (valid = authored by the given name and in english)
            start_time = time.time()
            books = json.loads(response.decode("utf-8"))["results"]
            raw_text = ''
            with ThreadPoolExecutor() as executor:
                for result in executor.map(find_text, books, repeat(author_name.lower())):
                    if result is not None:
                        raw_text += result

            end_time = time.time()
            print('timed operation : load books : {}'.format(end_time - start_time))

            start_time = time.time()
            sliced_raw_text = chunk_up_text(raw_text)
            end_time = time.time()
            print('timed operation : chunk data : {}'.format(end_time - start_time))

            # make model from text
            start_time = time.time()
            markov_model = dict()
            with ThreadPoolExecutor() as executor:
                executor.map(load_higher_order_markov_model, repeat(markov_model), repeat(1), sliced_raw_text)
            end_time = time.time()
            print('timed operation : generate model : {}'.format(end_time - start_time))

            speech = generate_random_paragraph(markov_model)

        except:
            flash("I can't read anything from this author. Try someone else, or perhaps check your spelling. We all "
                  "make mistakes.")

    return render_template('empty.html', sample={"author_name": author_name, "speech": speech})


app = create_app()
