import redis
from os import environ

DOWNLOAD_FOLDER = "downloads"

SQLALCHEMY_DATABASE_URI = "sqlite:///language.db"

#File upload size configuration
MAX_CONTENT_LENGTH = 16 * 1000 * 1000

#Mail configuration
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = environ.get("MAIL_USERNAME")
MAIL_PASSWORD = environ.get("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = environ.get("MAIL_DEFAULT_SENDER")

#Mail testing configuration
TESTING = True
MAIL_SURPRESS_SEND = True

#Session configuration (redis)
SECRET_KEY = environ.get("SECRET_KEY")
SESSION_TYPE = "redis"
SESSION_PERMANENT = False
#app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)
SESSION_USE_SIGNER = True
SESSION_REDIS = redis.from_url(environ.get("REDIS_URL"))