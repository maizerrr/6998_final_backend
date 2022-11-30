# 6998_final_backend
serverless backend running on google app engine

## Endpoint
https://glass-mantra-365915.ue.r.appspot.com

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

- /import \[login_required\]
  - GET: return a list of existing product sets
  - POST: expect json query, return success or not

- /import/{product_set_id} \[login_required\]
  - DELETE: delete the given product set (files on gcs will not be removed)

- /import/{operation_id} \[login_required\]
  - GET: return the status of an import operation

## Input format
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