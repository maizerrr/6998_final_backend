from pyspark.sql import SparkSession
from bs4 import BeautifulSoup
import requests
import json
import os

from google.cloud import storage
from google.oauth2 import service_account


# configs
urls = []
urls.append('https://www2.hm.com/en_us/search-results.html?q=clothes&department=ladies_all&sort=ascPrice&image-size=small&image=stillLife&offset=0&page-size=2400')
urls.append('https://www2.hm.com/en_us/search-results.html?q=clothes&department=ladies_all&sort=descPrice&image-size=small&image=stillLife&offset=0&page-size=2400')
urls.append('https://www2.hm.com/en_us/search-results.html?q=clothes&department=men_all&sort=descPrice&image-size=small&image=stillLife&offset=0&page-size=2034')

bucket_name = "6998_sample_data_2"
product_set_id = "product_set1"
category = "apparel-v2"


# init spark app
spark = SparkSession.builder \
    .master("local[*]") \
    .appName("SparkByExamples.com") \
    .getOrCreate() 

sc = spark.sparkContext


# define helper functions
def send_request(url):
    headers = headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content,'lxml')
    products = soup.find_all('article', {'class': 'hm-product-item'})
    rows = []
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
            
            rows.append(row)
        except Exception as e:
            continue
    return rows


def upload_data(row):
    json_key = Key.value
    bucket = get_bucket(json_key)
    if not bucket:
        return
    
    try:
        # img_data = requests.get(row[1]).content
        blob_name = row[6] + '.jpg'
        # blob = bucket.blob(blob_name)
        # blob.upload_from_string(img_data, content_type='image/jpeg')
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



# start scraping
if __name__ == "__main__":
    Key = sc.broadcast(json.loads(os.getenv('GCP_KEY')))

    urls = sc.parallelize(urls)
    products = urls.flatMap(send_request)
    indices = products.map(upload_data)

    indices.map(to_csv).coalesce(1)
    res = indices.collect()
    print()
    print(len(res))
    print(res[:5])