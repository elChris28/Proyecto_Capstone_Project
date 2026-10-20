import pytest
from werkzeug.security import generate_password_hash
from app import create_app

@pytest.fixture
def prod(monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('SECRET_KEY','a'*50)
    monkeypatch.setenv('ADMIN_USERNAME','supervisor')
    monkeypatch.setenv('ADMIN_PASSWORD_HASH',generate_password_hash('password-for-tests'))
    monkeypatch.delenv('CAPSTONE_FORCE_HTTPS',raising=False)
    a=create_app();a.config['TESTING']=True
    return a

def test_prod_rejects_missing_auth_config(monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.delenv('ADMIN_PASSWORD_HASH',raising=False)
    monkeypatch.delenv('SECRET_KEY',raising=False)
    with pytest.raises(RuntimeError): create_app()

def test_prod_requires_login(prod):
    with prod.test_client() as c:
        r=c.get('/api/predicciones-stock')
        assert r.status_code==401
        r=c.get('/calidad-datos')
        assert r.status_code==302 and '/login' in r.location

def test_login_rejects_bad_password(prod):
    with prod.test_client() as c:
        response=c.post('/login',data={'username':'supervisor','password':'wrong'})
        assert response.status_code==200
        assert 'incorrectos' in response.get_data(as_text=True)

def test_login_sets_csrf_and_protects_write(prod):
    with prod.test_client() as c:
        response=c.post('/login',data={'username':'supervisor','password':'password-for-tests'})
        assert response.status_code==302
        with c.session_transaction() as ses:
            assert ses['user']=='supervisor'
            token=ses['csrf_token']
        response=c.post('/logout')
        assert response.status_code==403
        response=c.post('/logout',data={'csrf_token':token})
        assert response.status_code==302

def test_ssl_header_prod(prod):
    with prod.test_client() as c:
        r=c.get('/health',base_url='https://example.test')
        assert r.headers['Strict-Transport-Security'].startswith('max-age=')
