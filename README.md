# 6998_final_backend
serverless backend running on google app engine

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

- /upload \[login_required\]
  - POST: expect csv containing filenames and gs links, return success or not

## Product Search Query
```
{
    'imageBlob': <base64 encoded> [required],
    'size': <Integer 1~500> [required],
    'productSetId': <String>,
    'category': 'homegoods-v2' | 'apparel-v2' | 'toys-v2' | 'packagedgoods-v1' | 'general-v1',
    'endpoint': <Url>,
    'boundingPoly': <JSON String>
}
```