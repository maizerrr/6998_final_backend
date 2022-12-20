#!/usr/bin/env python
# coding: utf-8

# In[26]:


import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


# In[43]:


"Men's PRIMALOFT® Jacket".find('Men')


# In[52]:


import time
# latest version!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
browser = webdriver.Chrome()

link = "https://www.nike.com/w/mens-shoes-nik1zy7ok"
women = 'ladies'
men = 'men'

browser.get(link)
time.sleep(1)

elem = browser.find_element(By.TAG_NAME,"body")

no_of_pagedowns = 500

while no_of_pagedowns:
    elem.send_keys(Keys.PAGE_DOWN)
    time.sleep(0.2)
    no_of_pagedowns-=1

name = []
image = []
plink = []
price = []
gender = []
category = []
product_id_array = []
products = browser.find_elements(By.CLASS_NAME,"product-card__body")
for product in products:
    y = product.find_element(By.CLASS_NAME,'product-card__link-overlay')
    product_name = y.text
    
    product_link = y.get_attribute('href')
    
    
    html_product = requests.get(product_link)
    soup_product = BeautifulSoup(html_product.text, 'html.parser')
    category_content = soup_product.find('h2', {'data-test':'product-sub-title'})
    price_content = soup_product.find(attrs={"property" : "og:price:amount"})
    product_id =  product_link.split('/')
    product_id = product_id[-1]

    if category_content is None or price_content is None:
        continue
    else:
        category_content = category_content.get_text()
        price_content = price_content.get("content")
    
    if category_content.find('Women')==0 or category_content.find('women')==0:
        gender_content = 'ladies'
    else:
        gender_content = 'men'
        print('tohere')
    image_link = soup_product.find_all(attrs={"property" : "og:image"})
    image_link = image_link[0]['content']
    print(product_name)
    print(product_id)
    print(product_link)
    print(image_link)
    print(category_content)
    print(price_content)
    print()
    if image_link.endswith('png') and product_name != '' and category_content!='' and price_content != '':
        name.append(product_name)
        plink.append(product_link)
        image.append(image_link)
        category.append(category_content)
        gender.append(gender_content)
        price.append(price_content)
        product_id_array.append(product_id)


# In[54]:


df = pd.DataFrame({'id': product_id_array,
                   'product_name': name,
                   'product_link': plink,
                   'product_image':image,
                   'category':category,
                   'price': price,
                   'gender': gender
                  })
# gender category price
print(df.shape)
df.head()
df.to_csv('nike_data.csv', mode='a', index = False, header=False)
#df.to_csv('nike_data.csv', header=True,index=False)


# # update csv if found new clothing

# In[ ]:


import time
# latest version!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
browser = webdriver.Chrome()

link = "https://www.nike.com/w/new-mens-3n82yznik1"
women = 'ladies'
men = 'men'

browser.get(link)
time.sleep(1)

elem = browser.find_element(By.TAG_NAME,"body")

no_of_pagedowns = 500

while no_of_pagedowns:
    elem.send_keys(Keys.PAGE_DOWN)
    time.sleep(0.2)
    no_of_pagedowns-=1

name = []
image = []
plink = []
price = []
gender = []
category = []
product_id_array = []
products = browser.find_elements(By.CLASS_NAME,"product-card__body")
for product in products:
    y = product.find_element(By.CLASS_NAME,'product-card__link-overlay')
    product_name = y.text
    
    product_link = y.get_attribute('href')
    
    
    html_product = requests.get(product_link)
    soup_product = BeautifulSoup(html_product.text, 'html.parser')
    category_content = soup_product.find('h2', {'data-test':'product-sub-title'})
    price_content = soup_product.find(attrs={"property" : "og:price:amount"})
    product_id =  product_link.split('/')
    product_id = product_id[-1]

    if category_content is None or price_content is None:
        continue
    else:
        category_content = category_content.get_text()
        price_content = price_content.get("content")
    
    if category_content.find('Women') or category_content.find('women'):
        gender_content = 'ladies'
    else:
        gender_content = 'men'
    image_link = soup_product.find_all(attrs={"property" : "og:image"})
    image_link = image_link[0]['content']
    print(product_name)
    print(product_id)
    print(product_link)
    print(image_link)
    print(category_content)
    print(price_content)
    print()
    if image_link.endswith('png') and product_name != '' and category_content!='' and price_content != '':
        dataset_id = 
            name.append(product_name)
            plink.append(product_link)
            image.append(image_link)
            category.append(category_content)
            gender.append(gender_content)
            price.append(price_content)
            product_id_array.append(product_id)


# # download Images

# In[67]:


from bs4 import *
import requests
import os
def download_image(url, file_name):
    # Send GET request
    response = requests.get(url)
    # Save the image
    if response.status_code == 200:
        with open(file_name, "wb") as f:
            f.write(response.content)
    else:
        print(response.status_code)

saved_clothing = pd.read_csv('nike_data.csv')
folder_path = 'images/'


# In[70]:


for i in range(len(saved_clothing['product_image'])):
    image_url = saved_clothing['product_image'][i]
    img_data = requests.get(image_url)
    with open((folder_path+saved_clothing['id'][i]+'.png'),'wb') as f:
        f.write(img_data.content)


# In[ ]:




