from flask import Flask, Response, request
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime, timedelta
from  werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy
import jwt
import json
import sys
import os

from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage
from google.oauth2 import service_account

from base64 import b64encode


'''
Initializing app
-----------------------------------------------------------
'''
# Default values & api keys
GCP_KEY = json.loads(os.getenv('GCP_KEY'))
SEARCH_CONFIG = {
    'project_id': None,
    'location': 'us-east1',
    'product_set_id': 'product_set0',
    'product_category': 'apparel-v2',
    'endpoint': 'https://vision.googleapis.com/v1'
}
TIMEOUT = 30

_DEFAULT_URL_EXPIRATION = timedelta(minutes=30)
_DEFAULT_SCOPES = (
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/cloud-vision',
)


# TODO: link to database
if os.getenv('DB_CRED'):
    DB_CRED = json.loads(os.getenv('DB_CRED'))
    DB_URI = sqlalchemy.engine.url.URL.create(
        drivername="mysql+pymysql",
        username=DB_CRED['username'],
        password=DB_CRED['password'],
        database=DB_CRED['database'],
        query={ 'unix_socket': DB_CRED['unix_socket'] }
    )
else:
    DB_URI = os.getenv('DB_URI')


# Create the Flask application object.
application = app = Flask(__name__)
app.config['SECRET_KEY'] = json.dumps(GCP_KEY)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
db = SQLAlchemy(app)


'''
User login
-----------------------------------------------------------
'''
class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(70), nullable=False, unique = True)
    password = db.Column(db.String(300), nullable=False)
    admin = db.Column(db.Boolean)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        else:
            return _Denied('Access token is missing')
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query\
                .filter_by(email = data['email'])\
                .first()
        except Exception as e:
            return _Denied(str(e))

        if not data or not current_user:
            return _Denied('User no longer exists')

        return f(current_user, *args, **kargs)
    return decorated



'''
Define routes
-----------------------------------------------------------
'''
# index page
@app.route('/')
def get_health():
    t = str(datetime.now())
    msg = {
        "name": "6998-FinalProject-backend",
        "health": "Good",
        "at time": t
    }
    return _Success(msg)


# search
@app.route('/search', methods=["POST"])
def search():
    query = parse_product_search_request(request)
    if type(query) == type(''):
        return _Error(query)
    (json_key, endpoint, product_search_request_json) = query
    
    cred = get_authed_session(json_key)
    if type(cred) == type(Exception):
        return _Error(cred, msg="Error retrieving google authed session")
    (_, authed_session) = cred
    
    try:
        url = os.path.join(endpoint, 'images:annotate')
        response = authed_session.post( url=url, data=json.dumps(product_search_request_json) ).json()
    except Exception as e:
        return _Error(e, msg="Internal error when calling google vision api")
    
    try:
        results = response["responses"][0]["productSearchResults"]["results"]
        for i in range(len(results)):
            product = results[i]["image"]
            img = get_match_image(product, endpoint)
            if type(img) == type( ('',) ) and len(img) == 2:
                msg, e = img
                return _Error(e, msg)
            results[i]['image'] = img['image_url']
    except Exception as e:
        return _Error(e, msg=str(response))

    return _Success(response)


# import data
@app.route('/import', methods=["POST"])
@login_required
def upload(current_user):
    if not current_user.admin:
        return _Denied("User {} does not have administration permission".format(current_user.email), status=403)

    (url, body) = import_request(request)
    if body is not None:
        url = os.path.join(url, 'productSets:import')
    else:
        return _Error("Invalid gcs_uri provided")

    cred = get_authed_session()
    if type(cred) == type(Exception):
        return _Error(cred, msg="Error retrieving google authed session")
    (_, authed_session) = cred

    try:
        response = authed_session.post( url=url, data=json.dumps(body) ).json()
    except Exception as e:
        return _Error(e, msg="Internal error when calling google vision api")

    return _Success(response)


# check import status
@app.route('/import/<operation_id>', methods=["GET"])
@login_required
def upload_status(current_user, operation_id):
    if not current_user.admin:
        return _Denied("User {} does not have administration permission".format(current_user.email), status=403)

    url = os.path.join( import_request(request)[0], 'operations', operation_id )

    cred = get_authed_session()
    if type(cred) == type(Exception):
        return _Error(cred, msg="Error retrieving google authed session")
    (_, authed_session) = cred

    try:
        response = authed_session.get( url=url ).json()
    except Exception as e:
        return _Error(e, msg="Internal error when calling google vision api")

    return _Success(response)



# list product sets
@app.route('/import', methods=["GET"])
@login_required
def show_sets(current_user):
    if not current_user.admin:
        return _Denied("User {} does not have administration permission".format(current_user.email), status=403)

    url = os.path.join( import_request(request)[0], 'productSets' )

    cred = get_authed_session()
    if type(cred) == type(Exception):
        return _Error(cred, msg="Error retrieving google authed session")
    (_, authed_session) = cred

    try:
        response = authed_session.get( url=url ).json()
    except Exception as e:
        return _Error(e, msg="Internal error when calling google vision api")

    return _Success(response)


# delete a product set
@app.route('/import/<product_set_id>', methods=["DELETE"])
@login_required
def delete_set(current_user, product_set_id):
    if not current_user.admin:
        return _Denied("User {} does not have administration permission".format(current_user.email), status=403)

    url = os.path.join( import_request(request)[0], 'productSets', product_set_id )

    cred = get_authed_session()
    if type(cred) == type(Exception):
        return _Error(cred, msg="Error retrieving google authed session")
    (_, authed_session) = cred

    try:
        response = authed_session.delete( url=url ).json()
    except Exception as e:
        return _Error(e, msg="Internal error when calling google vision api")

    return _Success(response)


# login
@app.route('/login', methods=["POST"])
def login():
    auth = request.form

    if not auth or not auth.get('email') or not auth.get('password'):
        return _Denied('Please provide login credentials')
    
    user = User.query\
        .filter_by(email = auth.get('email'))\
        .first()

    if not user:
        return _Denied('Username or password incorrect', status=403)

    if check_password_hash(user.password, auth.get('password')):
        token = jwt.encode(
            {
                'email': user.email,
                'exp': datetime.utcnow() + timedelta(minutes=TIMEOUT)
            },
            app.config['SECRET_KEY'], 
            algorithm="HS256"
        )
        return _Success({ 'token': token })

    return _Denied('Username or password incorrect', status=403)


# signup
@app.route('/signup', methods=["POST"])
def signup():
    data = request.form

    if not data or not data.get('email') or not data.get('password'):
        return _Denied('Please provide user email and password')

    user = User.query\
        .filter_by(email = data.get('email'))\
        .first()

    if not user:
        user = User(
            email = data.get('email'),
            password = generate_password_hash(data.get('password'))
        )
        db.session.add(user)
        db.session.commit()
        return _Success( { 'msg': 'Successfully registered' } )
    else:
        return _Denied( 'User already exists. Please Log in.', status=202 )

# user profile
@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile(current_user):
    if request.method == "POST":
        data = request.form
        if data.get('email'):
            current_user.email = data.get('email')
        if data.get('password'):
            current_user.password = generate_password_hash(data.get('password'))

    db.session.commit()

    res = {
        'id': current_user.id,
        'email': current_user.email,
        'admin': current_user.admin == True
    }
    return _Success(res)


'''
Helper methods
-----------------------------------------------------------
'''
def _Success(msg):
    res = Response(json.dumps(msg), status=200, content_type="application/json")
    res.headers["Access-Control-Allow-Origin"] = "*"
    res.headers["Access-Control-Allow-Headers"] = "*"
    res.headers["Access-Control-Allow-Methods"] = "*"
    return res

def _Error(e, msg="an error occured"):
    res = {
        'message': msg,
        'error': str(e)
    }
    res = Response(json.dumps(res), status=500, content_type="application/json")
    res.headers["Access-Control-Allow-Origin"] = "*"
    res.headers["Access-Control-Allow-Headers"] = "*"
    res.headers["Access-Control-Allow-Methods"] = "*"
    return res

def _Denied(msg, status=401):
    res = {
        'message': 'Unauthorized' if status==401 else 'Forbidden',
        'error': msg
    }
    res = Response(json.dumps(res), status=status, content_type="application/json")
    res.headers["Access-Control-Allow-Origin"] = "*"
    res.headers["Access-Control-Allow-Headers"] = "*"
    res.headers["Access-Control-Allow-Methods"] = "*"
    return res


def get_authed_session(json_key=GCP_KEY):
    try:
        credentials = service_account.Credentials.from_service_account_info(json_key)
        scoped_credentials = credentials.with_scopes(_DEFAULT_SCOPES)
        authed_session = AuthorizedSession(scoped_credentials)
    except Exception as e:
        return e
    return (credentials, authed_session)


def ParseBoundingPoly(poly_str):
    if not poly_str:
        return None
    json_poly = json.loads(poly_str)
    return {
        'normalized_vertices': [
            {
                'x': json_poly['x_min'],
                'y': json_poly['y_min']
            }, 
            {
                'x': json_poly['x_min'],
                'y': json_poly['y_max']
            }, 
            {
                'x': json_poly['x_max'],
                'y': json_poly['y_min']
            }, 
            {
                'x': json_poly['x_max'],
                'y': json_poly['y_max']
            }, 
        ]
    }


def parse_product_search_request(req):
    image_file = req.files.get('imageBlob', None)
    if not image_file:
        return "Invalid image"
    try:
        content = image_file.read()
    except ValueError:
        return "Invalid image file"

    product_set_id = req.form.get('productSetId', '')
    if product_set_id == '':
        product_set_id = SEARCH_CONFIG['product_set_id']
    
    product_category = req.form.get('category', '')
    if product_category == '':
        product_category = SEARCH_CONFIG['product_category']

    endpoint = req.form.get('endpoint', '')
    if endpoint == '':
        endpoint = SEARCH_CONFIG['endpoint']

    location = req.form.get('location', '')
    if location == '':
        location = SEARCH_CONFIG['location']

    json_key = GCP_KEY
    product_set = 'projects/' +\
        GCP_KEY['project_id'] + '/locations/' +\
        location + '/productSets/' +\
        product_set_id
    
    try:
        bounding_poly = ParseBoundingPoly(req.form.get('boundingPoly', ''))
    except (ValueError, TypeError):
        return "Invalid bounding poly format"

    try:
        max_results = int(req.form.get('size', None))
        if max_results <= 0 or max_results > 500:
            return "Size must between 1~500"
    except (ValueError, TypeError):
        return "Invalid size"

    product_search_request_json = {
        'requests': [{
            'image': {
                'content': b64encode(content).decode('ascii'),
            },
            'features': [{
                'type': 'PRODUCT_SEARCH',
                'max_results': max_results,
                'model': 'builtin/latest',
            }],
            'image_context': {
                'product_search_params': {
                    'product_set': product_set,
                    'product_categories': [product_category],
                    'bounding_poly': bounding_poly if bounding_poly else {},
                },
            },
        }],
    }

    return (json_key, endpoint, product_search_request_json)


def get_match_image(product, endpoint):
    try:
        img = product.split('/')[5]
    except Exception as e:
        return ("Invalid product/item", e)
    url = os.path.join(endpoint, product)

    cred = get_authed_session()
    if type(cred) == type(Exception):
        return _Error(cred, msg="Error retrieving google authed session")
    (credentials, authed_session) = cred

    try:
        response = authed_session.get(url=url).json()
    except Exception as e:
        return ("Image not found", e)
    
    if 'uri' not in response:
        return ("Image {} not found".format(img), str(response))

    try:
        gcs_client = storage.Client( project=GCP_KEY["project_id"], credentials=credentials )
        bucket, path = parse_gcs_uri(response["uri"])
        blob = gcs_client.bucket(bucket).blob(path)
    except Exception as e:
        return ("Failed to retrieve file from google cloud storage", e)
    
    return {
        'image_url': blob.generate_signed_url(_DEFAULT_URL_EXPIRATION),
        'label': img
    }


def parse_gcs_uri(gcs_uri):
    splitted = gcs_uri.split('/')
    if len(splitted) < 4:
        return None, None
    return splitted[2], '/'.join(splitted[3:])


def import_request(req):
    gcs_uri = req.form.get('gcs_uri', '')

    endpoint = req.form.get('endpoint', '')
    if endpoint == '':
        endpoint = req.args.get('endpoint', '')
        if endpoint == '':
            endpoint = SEARCH_CONFIG['endpoint']
    
    location = req.form.get('location', '')
    if location == '':
        location = req.args.get('endpoint', '')
        if location == '':
            location = SEARCH_CONFIG['location']

    url = os.path.join(endpoint, 'projects', GCP_KEY['project_id'], 'locations', location)
    body = {
        'input_config': {
            'gcs_source': {
                'csv_file_uri': gcs_uri
            }
        }
    }

    if 'gs://' not in gcs_uri or '.csv' not in gcs_uri:
        body = None

    return (url, body)

'''
Start flask server
-----------------------------------------------------------
'''
if __name__=="__main__":
    try:
        port = os.environ['port']
    except:
        port = 5000
    app.run(port=port)