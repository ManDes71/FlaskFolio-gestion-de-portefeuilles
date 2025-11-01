# tests/test_app.py
import unittest
import sys
import os

# Ajouter le répertoire parent au path pour pouvoir importer l'app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pea_trading import app, db
from pea_trading.users.models import User


class BasicTestCase(unittest.TestCase):
    """Tests de base pour l'application"""

    def setUp(self):
        """Configuration avant chaque test"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Nettoyage après chaque test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_app_exists(self):
        """Test que l'application existe"""
        self.assertIsNotNone(app)

    def test_app_is_testing(self):
        """Test que l'application est en mode test"""
        self.assertTrue(app.config['TESTING'])

    def test_index_redirect(self):
        """Test que la route principale redirige correctement"""
        response = self.client.get('/')
        # Vérifie une redirection (code 302) ou une réponse réussie (code 200)
        self.assertIn(response.status_code, [200, 302])

    def test_login_page_loads(self):
        """Test que la page de connexion se charge"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

    def test_register_page_loads(self):
        """Test que la page d'inscription se charge"""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)


class UserModelTestCase(unittest.TestCase):
    """Tests pour le modèle User"""

    def setUp(self):
        """Configuration avant chaque test"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Nettoyage après chaque test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_password_hashing(self):
        """Test que les mots de passe sont hashés correctement"""
        with app.app_context():
            user = User(email='test@example.com', username='testuser', password='secret')
            # Le mot de passe ne doit pas être stocké en clair
            self.assertNotEqual(user.password_hash, 'secret')
            # La vérification du mot de passe doit fonctionner
            self.assertTrue(user.check_password('secret'))
            self.assertFalse(user.check_password('wrong'))


if __name__ == '__main__':
    unittest.main()
