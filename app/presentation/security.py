"""Controles mínimos de acceso para entornos productivos de VetAssistant IA.

En desarrollo local, autenticación desactivada. En APP_ENV=production,
la aplicación rechaza el arranque sin credenciales y secreto explícitos.
"""
from __future__ import annotations
import os
import secrets
from flask import abort, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

PROTECTED_METHODS={'POST','PUT','PATCH','DELETE'}

def setup_security(app):
    production=os.getenv('APP_ENV','development').lower() == 'production'
    password_hash=os.getenv('ADMIN_PASSWORD_HASH','').strip()
    username=os.getenv('ADMIN_USERNAME','admin').strip()
    secret=os.getenv('SECRET_KEY','')
    if production:
        if not secret or secret in ('inventario_ml_secret','change-me') or len(secret)<32:
            raise RuntimeError('Producción exige SECRET_KEY explícita de al menos 32 caracteres.')
        if not password_hash or not username:
            raise RuntimeError('Producción exige ADMIN_USERNAME y ADMIN_PASSWORD_HASH.')
    app.config.update(CAPSTONE_PRODUCTION=production,ADMIN_USERNAME=username,
                      ADMIN_PASSWORD_HASH=password_hash,
                      SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=production)

    @app.before_request
    def secure_requests():
        if not app.config['CAPSTONE_PRODUCTION']:
            return None
        # Al desplegar detrás de un proxy HTTPS, activar CAPSTONE_FORCE_HTTPS=1.
        if os.getenv('CAPSTONE_FORCE_HTTPS','0') == '1' and not request.is_secure:
            return jsonify({'error':'HTTPS requerido'}),403
        if request.endpoint in ('security_login','healthcheck','static'):
            return None
        if session.get('user') != app.config['ADMIN_USERNAME']:
            if request.path.startswith('/api/'):
                return jsonify({'error':'Autenticación requerida'}),401
            return redirect(url_for('security_login',next=request.path))
        if request.method in PROTECTED_METHODS:
            sent=request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not sent or not secrets.compare_digest(str(sent),str(session.get('csrf_token') or '')):
                abort(403,description='CSRF inválido')
        return None

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['Cache-Control']='no-store' if request.path.startswith('/api/') else 'private, no-cache'
        if request.is_secure and production:
            response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
        return response

    @app.context_processor
    def expose_csrf_token():
        return {'csrf_token':session.get('csrf_token','')}

    @app.route('/login',methods=['GET','POST'],endpoint='security_login')
    def login():
        if not app.config['CAPSTONE_PRODUCTION']:
            return redirect(url_for('assistant.index'))
        error=None
        if request.method=='POST':
            user=request.form.get('username','')
            password=request.form.get('password','')
            if (secrets.compare_digest(user,app.config['ADMIN_USERNAME'])
                and check_password_hash(app.config['ADMIN_PASSWORD_HASH'], password)):
                session.clear()
                session['user']=user
                session['csrf_token']=secrets.token_urlsafe(32)
                return redirect(url_for('assistant.index'))
            error='Usuario o contraseña incorrectos.'
        return render_template('login.html',error=error)

    @app.route('/logout',methods=['POST'],endpoint='security_logout')
    def logout():
        session.clear()
        return redirect(url_for('security_login'))

    @app.route('/health',endpoint='healthcheck')
    def health():
        # No revela versión, modelo, credenciales ni información de clientes.
        return jsonify({'estado':'activo'})
