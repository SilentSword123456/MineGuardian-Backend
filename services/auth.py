import os
from apiflask import APIBlueprint
from flask import make_response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from Database import repositories
from Database.repositories import UserRepository
from services.docs import DOCS
from services.schemas import LoginRequestSchema, LoginOutputSchema, StatusOutputSchema

jwt = JWTManager()

auth_blueprint = APIBlueprint('auth', __name__)

# Cookies are only secure (HTTPS-only) outside of development.
# Set FLASK_ENV=development in your environment (or a local .env file) to
# allow cookies over plain HTTP during local development.
_secure_cookies = os.environ.get('FLASK_ENV', 'production') != 'development'
_cookie_samesite = "None" if _secure_cookies else "Lax"

@auth_blueprint.route('/login', methods=['POST'])
@auth_blueprint.doc(**DOCS['login'])
@auth_blueprint.input(LoginRequestSchema, location='json', arg_name='request_data', validation=False)
@auth_blueprint.output(LoginOutputSchema, status_code=200)
def login(request_data=None):
    if request_data is None:
        return make_response({'message': 'Missing user_id or password'}, 400)

    username = request_data.get('user_id')
    password = request_data.get('password')

    if username is None or password is None:
        return make_response({'message': 'Missing user_id or password'}, 400)

    authorized = repositories.UserRepository.verify(username, password)
    if not authorized:
        return make_response({'message': 'Invalid credentials'}, 401)

    userId = repositories.UserRepository.getUserId(username)
    access_token = create_access_token(identity=str(userId))
    response = make_response()

    response.set_cookie(
        "accessToken",
        access_token,
        httponly=True,
        secure=_secure_cookies,
        samesite=_cookie_samesite
    )
    return response

@auth_blueprint.route('/isSessionValid', methods=['GET'])
@auth_blueprint.doc(**DOCS['is_session_valid'])
@auth_blueprint.output(StatusOutputSchema, status_code=200)
@jwt_required()
def isSessionValid():
    identity = get_jwt_identity()
    try:
        userId = int(identity)
    except (TypeError, ValueError):
        return {'status': False}, 401

    if not UserRepository.doseUserExist(userId):
        return {'status': False}, 401

    return {'status': True}, 200

