import os
from dotenv import load_dotenv

#pip install python-dotenv

# 🔍 On récupère le chemin absolu du .env (à la racine du projet)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
print("env_path = ",env_path)
load_dotenv(dotenv_path=env_path)


#print("Clé secrète :", os.getenv('SECRET_KEY'))
#print("MAIL_USERNAME :", os.getenv('MAIL_USERNAME'))
#print("MAIL_PASSWORD :", os.getenv('MAIL_PASSWORD'))
#print("DATABASE_URL :", os.getenv('DATABASE_URL'))


class Config:
    DEBUG = False  # Valeur par défaut

    # Configuration de la base de données
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///finance.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    
    # Clé secrète pour la sécurité
    SECRET_KEY = os.getenv('SECRET_KEY')

    

    # Configuration de l'envoi SMTP
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'manuel.desplanches@gmail.com'
    MAIL_DEBUG = False
    SERVER_NAME = '127.0.0.1:5000'  # ou ton vrai domaine en prod
    PREFERRED_URL_SCHEME = 'http'

class DevConfig(Config):
    DEBUG = True
    TESTING = False


class TestConfig(Config):
    DEBUG = True
    TESTING = True


class ProdConfig(Config):
    DEBUG = False
    TESTING = False


