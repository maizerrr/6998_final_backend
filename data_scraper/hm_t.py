from tqdm import tqdm
from multiprocessing.pool import ThreadPool
from multiprocessing import Manager
from bs4 import BeautifulSoup
from email.message import EmailMessage
from datetime import datetime
import requests
import base64
import boto3
import json
import os

from google.cloud import storage
from google.oauth2 import service_account


# configs
NUM_OF_T = 8
CSV = "product_catalog.csv"
ADMIN = "yt2777@columbia.edu"

urls = []
urls.append('https://www2.hm.com/en_us/search-results.html?q=clothes&department=ladies_all&sort=ascPrice&image-size=small&image=stillLife&offset=0&page-size=2400')
urls.append('https://www2.hm.com/en_us/search-results.html?q=clothes&department=ladies_all&sort=descPrice&image-size=small&image=stillLife&offset=0&page-size=2400')
urls.append('https://www2.hm.com/en_us/search-results.html?q=clothes&department=men_all&sort=descPrice&image-size=small&image=stillLife&offset=0&page-size=2034')

bucket_name = "6998_sample_data_2"
product_set_id = "product_set1"
category = "apparel-v2"


# define helper functions
def send_request(L, url):
    headers = headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content,'lxml')
    products = soup.find_all('article', {'class': 'hm-product-item'})
    for item in products:
        try:
            color = []
            for swatch in item.select('.swatch'):
                color.append(swatch.get_text().strip())
            row = [
                item["data-category"],                                  # category
                'http:'+item.select('.item-image')[0]['data-altimage'], # image
                item.select('.item-price')[0].get_text().strip(),       # price
                item.select('.item-image')[0]['data-alttext'] ,         # product
                color[0],                                               # color
                'https://www2.hm.com'+item.select('.link')[0]['href']   # product link
            ]

            product_id = row[-1][ row[-1].find("productpage.")+12 : row[-1].find(".html") ]
            row.append(product_id)

            gender_category = row[0].split("_")
            row[0] = gender_category[1]
            row.append(gender_category[0])

            row[3] = row[3][:-5]
            
            L.append(row)
        except Exception as e:
            continue


def parse_response(L, bucket, start, end, pbar=None):
    for i in range(start, end):
        L[i] = upload_data(L[i], bucket)
        if pbar:
            pbar.update(1)


def upload_data(row, bucket):
    try:
        img_data = requests.get(row[1]).content
        blob_name = row[6] + '.jpg'
        blob = bucket.blob(blob_name)
        blob.upload_from_string(img_data, content_type='image/jpeg')
    except Exception:
        return
    return [
        'gs://' + bucket_name + '/' + blob_name,
        'image_' + row[6],
        product_set_id,
        row[6],
        category,
        "{} {}".format(row[3], row[5]),
        "Color={},Gender={},Category={}".format(row[4],row[7],row[0]),
        None
    ]


def to_csv(row):
    res = ""
    for entry in row:
        if not entry:
            entry = ''
        if entry.find(',') != -1:
            entry = '"{}"'.format(entry)
        res = res + entry + ','
    return res[:-1]


def get_bucket(json_key):
    bucket = None
    try:
        credentials = service_account.Credentials.from_service_account_info(json_key)
        gcs_client = storage.Client( project=json_key["project_id"], credentials=credentials )
        bucket = gcs_client.create_bucket(bucket_name)
    except Exception as e:
        bucket = gcs_client.get_bucket(bucket_name)
    return bucket


def send_email(content):
    ses = boto3.client('ses')
    CHARSET = "UTF-8"
    return ses.send_email(
        Source='admin@spam.maizer.pw',
        Destination={
            'ToAddresses': [ADMIN],
        },
        Message={
            'Subject': {
                'Data': 'Data Scraper Notification',
                'Charset': CHARSET
            },
            'Body': {
                'Text': {
                    'Data': content,
                    'Charset': CHARSET
                }
            }
        }
    )


# start scraping
if __name__ == "__main__":
    try:
        json_key = json.loads(os.getenv('GCP_KEY'))
    except:
        json_key = json.load(open('gcp_key.json'))

    with Manager() as manager:
        products = manager.list()

        print("retrieving product list...")
        pool = ThreadPool(len(urls))
        for url in urls:
            pool.apply(send_request, args=(products, url))
        pool.close()
        pool.join()

        # print("for demonstration, limiting result size...")
        # products = products[:100]

        print("uploading result...")
        pool = ThreadPool(NUM_OF_T)
        break_point = 0
        bucket = get_bucket(json_key)
        with tqdm(total=len(products)) as pbar:
            for i in range(NUM_OF_T):
                start = break_point
                end = break_point + int(len(products) / NUM_OF_T)
                if i == NUM_OF_T - 1:
                    end = len(products) - 1
                pool.apply(parse_response, args=(products, bucket, start, end, pbar))
                break_point = end
            pool.close()
            pool.join()

        with open(CSV, 'w') as fout:
            for row in products:
                fout.write( to_csv(row)+'\n' )

        blob = bucket.blob(CSV)
        blob.upload_from_filename(CSV)
        gcs_uri = 'gs://' + bucket_name + '/' + CSV

        content = "Data scraping finished at {}. New data stored in the following file:\n\n{}".format(datetime.now(), gcs_uri)
        send_email(content)

    # os.system("shutdown now -h")