# 6998_final_backend
serverless backend running on google app engine

## Endpoint
https://glass-mantra-365915.ue.r.appspot.com

## Cloud Computing Services
- google cloud app engine
- google cloud storage
- google cloud sql
- google cloud vision api

## APIs
- /
  - GET: return health status of backend

- /login
  - POST: return session key

- /signup
  - POST: return success or not

- /search
  - POST: expect json query, return a list of urls

- /profile \[login_required\]
  - GET: return info of current user

- /import \[admin_required\]
  - GET: return a list of existing product sets
  - POST: expect json query, return success or not

- /import/{product_set_id} \[admin_required\]
  - DELETE: delete the given product set (files on gcs will not be removed)

- /import/{operation_id} \[admin_required\]
  - GET: return the status of an import operation

## Input format
**authentication**
Access token can be retrieved from '/login' route, and will expire after 30min
```
Header
  x-access-token: <token>
```

**product search query**
```
{
    'imageBlob': <base64 encoded> [required],
    'size': <Integer 1~500> [required],
    'productSetId': <String>,
    'category': 'homegoods-v2' | 'apparel-v2' | 'toys-v2' | 'packagedgoods-v1' | 'general-v1',
    'endpoint': <Url>,
    'location': <String>,
    'boundingPoly': <JSON String>
}
```

**import csv query**
```
{
    'gcs_uri': <gs link> [required],
    'endpoint': <Url>,
    'location': <String>
}
```

## References
1. flask token-based user login <a href='https://www.geeksforgeeks.org/using-jwt-for-user-authentication-in-flask/'>link</a>
2. cloud sql connection <a href='https://cloud.google.com/sql/docs/mysql/connect-app-engine-standard'>link\[1\]</a> <a href='https://stackoverflow.com/questions/72588424/app-engine-cant-connect-to-cloud-sql-connection-refused'>link\[2\]</a>