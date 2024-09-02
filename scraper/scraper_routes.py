# routes.py
from flask import Flask
from scraper.scraper_controller import check_validity

def create_app():
    app = Flask(__name__)
    app.route('/product/cv', methods=['POST', 'GET'])(check_validity)

    app.route('/')(lambda: "Ok,I am healthy!")
    return app
