from apiflask import APIBlueprint
from flask_jwt_extended import JWTManager, create_access_token
from Database import repositories
from services.docs import DOCS
from services.schemas import LoginRequestSchema, LoginOutputSchema

jwt = JWTManager()

auth_blueprint = APIBlueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['POST'])
@auth_blueprint.doc(**DOCS['login'])
@auth_blueprint.input(LoginRequestSchema, location='json', arg_name='request_data', validation=False)
@auth_blueprint.output(LoginOutputSchema, status_code=200)
def login(request_data=None):
    if request_data is None:
        return {'message': 'Missing user_id or password'}, 400

    username = request_data.get('user_id')
    password = request_data.get('password')

    if username is None or password is None:
        return {'message': 'Missing user_id or password'}, 400

    authorized = repositories.UserRepository.verify(username, password)
    if not authorized:
        return {'message': 'Invalid credentials'}, 401

    userId = repositories.UserRepository.getUserId(username)
    access_token = create_access_token(identity=str(userId))
    response = make_response()

    response.set_cookie(
        "accessToken",
        access_token,
        httponly=True,
        secure=False, #TODO CHANGE IN PRODUCTION
        samesite="Lax"
    )
    return response