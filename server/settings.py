import os
import logging


logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
logging.getLogger('facilities').level = logging.DEBUG


class DBConfiguration:
    debug = True
    APPLICATION_DIR = os.path.dirname(os.path.realpath(__file__))
    STATIC_DIR = os.path.join(APPLICATION_DIR, 'static')
    TEMPLATES_DIR = os.path.join(APPLICATION_DIR, 'templates')
    SQLALCHEMY_DATABASE_URI = "mysql://root:1@106.15.192.121:3306/easyterm"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
