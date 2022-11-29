from flask import Flask, Response, request
from flask_login import login_user, logout_user, login_required
from flask_cors import CORS
from datetime import datetime, timedelta
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
# TODO: link to database


# Create the Flask application object.
application = app = Flask(__name__)

CORS(app)


# Default values & api keys
GCP_KEY = json.loads(os.getenv('GCP_KEY'))
SEARCH_CONFIG = {
    'project_id': None,
    'location': 'us-east1',
    'product_set_id': 'product_set0',
    'product_category': 'apparel-v2',
    'endpoint': 'https://vision.googleapis.com/v1'
}

_DEFAULT_URL_EXPIRATION = timedelta(minutes=30)
_DEFAULT_SCOPES = (
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/cloud-vision',
)


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
    try:
        (json_key, endpoint, product_search_request_json) = query
        credentials = service_account.Credentials.from_service_account_info(json_key)
        scoped_credentials = credentials.with_scopes(_DEFAULT_SCOPES)
        authed_session = AuthorizedSession(scoped_credentials)
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


'''
Helper methods
-----------------------------------------------------------
'''
def _Success(msg):
    return Response(json.dumps(msg), status=200, content_type="application/json")

def _Error(e, msg="an error occured"):
    res = {
        'message': msg,
        'error': str(e)
    }
    return Response(json.dumps(res), status=500, content_type="application/json")


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

    json_key = GCP_KEY
    product_set = 'projects/' +\
        GCP_KEY['project_id'] + '/locations/' +\
        SEARCH_CONFIG['location'] + '/productSets/' +\
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

    json_key = GCP_KEY

    try:
        credentials = service_account.Credentials.from_service_account_info(json_key)
        scoped_credentials = credentials.with_scopes(_DEFAULT_SCOPES)
        authed_session = AuthorizedSession(scoped_credentials)
        response = authed_session.get(url=url).json()
    except Exception as e:
        return ("Image not found", e)
    
    if 'uri' not in response:
        return ("Image {} not found".format(img), str(response))

    try:
        gcs_client = storage.Client( project=json_key["project_id"], credentials=credentials )
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