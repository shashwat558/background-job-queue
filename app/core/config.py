import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY= os.getenv("SECRET_KEY")
GOOGLE_CLIENT_ID= os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET= os.getenv("GOOGLE_CLIENT_SECRET")
REDIS_HOST_URL = os.getenv("REDIS_HOST_URL")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

conf = ConnectionConfig(
    MAIL_USERNAME="jainshashwat528@gmail.com",
    MAIL_PASSWORD="aaft",
    MAIL_FROM = "jainshashwat528@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True 
)