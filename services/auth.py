from flask import Blueprint, request
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from Database import repositories

jwt = JWTManager()

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username is None or password is None:
        return {'message': 'Missing username or password'}, 400

    authorized = repositories.UserRepository.verify(username, password)
    if not authorized:
        return {'message': 'Invalid credentials'}, 401

    access_token = create_access_token(identity=username)
    return {'access_token': access_token}, 200


@auth_blueprint.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return {'logged_in_as': current_user}, 200