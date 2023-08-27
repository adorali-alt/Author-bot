import os
import markovify
import requests
import string
import json
import random
import time
from flask import (
    Flask, Blueprint, flash, render_template, request, make_response, jsonify
)

bp = Blueprint('generate', __name__, url_prefix='/')

GUT_URL_TEMPLATE = "http://gutendex.com/books?search="

# prevents insane load times from prolific writers
CORPUS_CHAR_LIMIT = 20000


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

def find_text(books, target_author):
    response = ""
    for book in books:
        if len(response) > CORPUS_CHAR_LIMIT:
            break

        # check author
        book_is_match = False
        for curr_book_author in book["authors"]:

            name_is_match = True
            for name in target_author.split():
                name_is_match = name_is_match and (name.casefold() in curr_book_author["name"].casefold())
            book_is_match = name_is_match

        # get book's text
        try:
            if book_is_match and (book['media_type'] == "Text") and ("en" in book["languages"]):
                if 'text/plain; charset=us-ascii' in book['formats']:
                    response += requests.get(book["formats"]['text/plain; charset=us-ascii']).content.decode("ascii", "ignore")
                elif 'text/plain' in book['formats']: 
                    response += requests.get(book["formats"]['text/plain']).content.decode("utf-8", "ignore")
                elif 'text/plain; charset=utf-8' in book['formats']:
                    response += requests.get(book["formats"]['text/plain; charset=us-ascii']).content.decode("utf-8", "ignore")
        except:
            pass # when text grabs fail, just keep going

    return response


@bp.route('/', methods=('GET', 'POST'))
def getFromLearningModel():
    author_name = "Author"
    speech = "..."

    # if they submitted their author:
    if request.method == 'POST' and request.form['name'] is not None:
        # replace spaces with url encoded version
        author_name = request.form['name']
        print(author_name)
        query = author_name.lower().replace(' ', '%20')
        # fetch book list
        try:
            start_time = time.time()
            response = requests.get(GUT_URL_TEMPLATE + query).content
            end_time = time.time()
            print('timed operation : get from gutendex : {}'.format(end_time - start_time))

            raw_text = find_text(json.loads(response.decode("utf-8"))["results"], author_name)
            if raw_text is None:
                raise Exception()

            text_model = markovify.Text(raw_text)

            speech = ""

            for i in range(7):
                # we want to let the sentence end naturally according to the author's style, so this only 
                # terminates run on sentences 
                speech += " " + text_model.make_short_sentence(400)

            print(speech)

        except:
            speech += "I can't read anything from "+author_name+". Try someone else, or perhaps check the spelling."

    # result = '{"authorName": '+author_name.title()+', "speech": '+speech+'}'
    # resp = make_response(jsonify(result), 200)
    # resp.headers['Content-Type'] = "application/json"
    # print(resp)
    return render_template('empty.html', sample={"author_name": author_name.title(), "speech": speech})
    # return render_template('base.html', message='') data=result, 
 

app = create_app()