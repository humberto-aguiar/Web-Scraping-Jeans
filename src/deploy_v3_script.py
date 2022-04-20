# Imports
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import gc
# functions

def request_soup(url_link):    
    headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'}    
    page = requests.get( url, headers = headers)
    soup_obj = BeautifulSoup(page.text, 'html.parser')
    return( soup_obj )

def composition_to_df(list_of_comp):
    """ Creates a dataframe from a list of compositions"""
    keys = []
    values = []

    for idx, element in enumerate(list_of_comp):
        # if idx is even, element is a key (column in dataframe)
        if idx % 2 == 0:
            keys.append(element)
        else:
            values.append(element.strip('%,'))

    # final dataframe
    res = dict(zip(keys,values))
    res = pd.DataFrame(res, index = [0])
    return (res)
# Data Requesting
##  Home Page Scraping
# all products url
url = 'https://www2.hm.com/en_us/men/products/jeans.html'

# headers for request
headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'}

# requesting
page = requests.get(url=url, headers=headers)

# instatiating bs4 object
soup = BeautifulSoup(page.text, 'html.parser')
# finding load more products element
p = soup.find('div', class_='load-more-products')

# all products
all_products = int(p.find('h2').get('data-total'))

# products per page
products_per_page = int(p.find('h2').get('data-items-shown'))

# rounding up numer of pages needed for web scraping
total_pages = np.ceil(all_products/products_per_page)

##  All products in Home Page Scraping
# creating a page with all products
url_all_prods = url + '?&offset=0&page-size={}'.format(int(total_pages*products_per_page))

all_prods = requests.get(url = url_all_prods, headers=headers)
soup = BeautifulSoup(all_prods.text, 'html.parser')#.get('li', class_='product-item')

# soup.find('li', class_ = 'product-item').find('a').get('href') #.get('item-link')  #.get('item-link') #, class_ = 'item-link')
# all find all products listed in homepage
products = soup.find_all('li', class_='product-item')

# get link to all projects
home_links = ['https://www2.hm.com' + link.find('a').get('href') for link in products ]
##  All products in Each Product Page
# resulting list of all products to scrap
links = []

for link in home_links:
    # scrap each product in home page list
    single_product = requests.get(link, headers = headers)
    soup = BeautifulSoup(single_product.text, 'html.parser')

    # gets the links to all products listed in a page
    products_ul = soup.find('ul', class_='inputlist clearfix')
    products = products_ul.find_all('a')

    links_ul = []
    links_ul = [ 'https://www2.hm.com' + item.get('href') for item in products]
    links.extend(links_ul)
# getting all unique products listed

# converting to a set and then back to list
links = list(set(links))
links.sort()
# defining base dataframe
df_prods = pd.DataFrame()

for link in links:
    
    # scrap each product in home page list
    single_product = requests.get(link, headers = headers)
    soup = BeautifulSoup(single_product.text, 'html.parser')
    
    # scrap all products listed in a page
    products_ul = soup.find('ul', class_='inputlist clearfix')
    products = products_ul.find_all('a')

    # product headline
    headline = soup.find('h1', class_='primary product-item-headline').text


    for product in products:
        
        #product it
        sku = product.get('data-articlecode')
       
        # color
        color = product.get('data-color')
        
        # product id
        product_id = sku[:-3]
        
        # style id
        color_id = sku[-3:]

        # link
        link = 'https://www2.hm.com/en_us/productpage.{}.html'.format(sku)

        df_temp = pd.DataFrame( {'sku': sku, 'product_id' :product_id, 'color_id' : color_id, 'color': color, 'headline' : headline, 'link': link}, index = [0] )
        
        df_prods = pd.concat([df_prods, df_temp], axis = 0)


df_prods.drop_duplicates('sku',inplace = True)

df_prods.reset_index(inplace = True, drop = True)
df_prods.head()
gc.collect()
## Individual Scraping
### Instantiating a Web Driver
# starting drive

options = Options()
options.headless = True
driver = webdriver.Firefox(options=options)

print('Starting Selenium Phase\n')
### Scrapping Everything
df_comp = pd.DataFrame()
# wait at max 120s
time_out = 120

for idx, link in enumerate(df_prods['link']):

    # sku
    sku = link.split('.')[3]
    print('scraping page {}/{}: {}'.format( idx+1, len(df_prods), link))
    
    # load web page
    driver.get(link)
    
    # get price
    # try this class (for no promo days)
    class_price = "ProductPrice-module--productItemPrice__2i2Hc"
    element = WebDriverWait(driver, timeout=time_out).until( EC.presence_of_element_located( (By.CLASS_NAME, class_price) ) )
    price = element.text

    # if element returns empty, try this other class
    if element.text == '':
        class_price = "price.parbase"
        element = WebDriverWait(driver, timeout=time_out).until( EC.presence_of_element_located( (By.CLASS_NAME, class_price) ) )
        price = element.text
        
        if price == '':
            price = 'NA'
    
    # get product description   
    class_desc = "ProductDescription-module--descriptionText__1zy9P"      
    # test if description exists
    try: 
        content = WebDriverWait(driver, timeout=time_out).until(EC.presence_of_element_located( (By.CLASS_NAME, class_desc) ))
        desc = content.text
    except:
        desc = 'NA'
    
    # get text
    class_text = 'ProductAttributesList-module--descriptionListItem__3vUL2'
    contents = WebDriverWait(driver, timeout=time_out).until( EC.presence_of_all_elements_located( (By.CLASS_NAME, class_text) ) )
    
    # concatenate all lines of text
    text = str()
    # list with all text
    text = [text + line.text  for line  in contents]

    # separate fit and composition from text
    # if fit or composition is not informed they'll return NA
    fit = 'NA'
    composition = 'NA'
    for element in text:
        if 'fit' in element:
            fit = element
        if 'Composition' in element:
            composition = element    
    
    # saving raw text
    text_raw =' /'.join(text)
    
    # saving results
    df_aux = pd.DataFrame( {'sku' : sku, 'price' : price, 'fit' : fit, 'composition' : composition, 'description' : desc ,'text' : text_raw,}, index = [0] )
    df_comp = pd.concat( [df_comp, df_aux], axis = 0 )     
    gc.collect()
df_comp.reset_index(inplace = True, drop = True)
driver.quit()
gc.collect()

print(df_comp.shape)
print(df_comp.head())
# Data Parsing
### Composition
# removing composition using regex

df_comp_aux = df_comp.copy()

comps = []
linings = []

for idx, text in enumerate(df_comp_aux['composition']):
    # case 1 pocket lining present
    if 'Pocket' in text:
        # regex = '(Shell: .*?=Pocket|Cotton.*(?=Pocket))'
        regex = 'Cotton.*(?=Pocket)'
        try:
            comp = re.findall( regex, text)[0]
        except:
            comp = 'NA'
    # case 2 pocket lining not present
    else:
        regex = '(Cotton.*(?=Lining)|Cotton.*(?=lining)|Cotton.*%)'
        try:
            comp = re.findall( regex, text)[0]
        except:
            comp = 'NA'
        # print(df_comp_aux.loc[idx, 'sku'] + '|' + text +' | ' + comp)
    
    # geting pocket composition:
    regex = '(?<=lining: ).*'
    try:
        lining = re.findall(regex, text)[0]
    except:
        lining = 'Not Informed'
    linings.append(lining)
    
    comps.append(comp)
df_comp_aux['comp'] = comps
df_comp_aux['lining'] = linings
# result
df_comp_aux.head()
# creating a dataframe for all compositions
df_comp_split = pd.DataFrame()

for composition in df_comp_aux['comp']:
    comp_list = composition.split(' ') 

    # creating a df of compositions
    df_aux = composition_to_df(comp_list)

    # concatenating results
    df_comp_split = pd.concat( [df_comp_split, df_aux], axis = 0 )

df_comp_split.reset_index(inplace = True, drop = True)
# result
df_comp_aux = pd.concat( [df_comp_aux, df_comp_split], axis = 1 )
df_comp_aux.head()

df_comp_aux.tail()
### Fit
# positive lookbehind + words I'm searching + positive lookahead
regex = "((?<=Fit).*(?= fit)|NA)"

df_comp_aux['fit'] = df_comp_aux['fit'].apply(lambda x: re.findall(regex, x)[0] )
df_comp_aux.head()
### Price
# regex = "\$\d{2}.\d{2}\$\d{2}.\d{2}"
# price = '$22.22$11.11'
# price = '$31.99$39.99'

# bool(re.match(regex, price ))
# df_comp_aux = df_comp_aux.copy()

# if there are 2 prices then there is a discount/promo
regex = "\$\d+\.\d+\$\d+.\d+"
df_comp_aux['isPromo'] = df_comp_aux['price'].apply(lambda x: 1 if bool(re.match(regex, x)) else 0)

# first price
regex = "^\$\d+\.\d+"
df_comp_aux['firstPrice'] = df_comp_aux['price'].apply( lambda x: re.findall(regex, x)[0] )

# second price
regex = "\$\d+\.\d+$"
df_comp_aux['secondPrice'] = df_comp_aux['price'].apply( lambda x: re.findall(regex, x)[0] )

# removing
df_comp_aux['firstPrice'] = df_comp_aux['firstPrice'].apply(lambda x: x.strip('$')).astype(float)
df_comp_aux['secondPrice'] = df_comp_aux['secondPrice'].apply(lambda x: x.strip('$')).astype(float)

# 
df_comp_aux['finalPrice'] = df_comp_aux.apply( lambda x: x['firstPrice'] if x['firstPrice'] <= x['secondPrice'] else x['secondPrice'], axis =1 )
df_comp_aux['originalPrice'] = df_comp_aux.apply( lambda x: x['secondPrice'] if x['secondPrice'] >= x['firstPrice'] else x['firstPrice'], axis =1 )

df_comp_aux.drop(['firstPrice', 'secondPrice'], axis = 1, inplace = True)
# df_comp_aux[df_comp_aux.firstPrice == df_comp_aux.secondPrice]
df_comp_aux.head()
print('Found {} promos'.format(df_comp_aux[df_comp_aux['isPromo']== True].shape[0]))
df_comp_aux[df_comp_aux['isPromo'] == True].tail()
### Headline
# removing whitespace characteres

df_prods['headline'] = df_prods['headline'].apply(lambda x: x.strip('\n\t ')) 
df_prods.headline.value_counts()
df_comp_aux.head()

df_final = pd.concat( [df_prods, df_comp_aux.drop('sku', axis = 1)], axis =1 )

# adding date time
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
df_final['date'] = now
df_final.head()
df_final.columns
#sku, product_id, color_id, color, fit, price, headline, 'cotton', 'polyester', 'elastane', 'elasterell_p', 'spandex' 'modal', 'viscose', pocket_lining, text

# selected_cols = ['sku', 'product_id', 'color_id', 'color', 'fit', 'finalPrice', 'originalPrice', "headline", 'Cotton', 'Polyester', 'Spandex', 'Modal', 'Elastomultiester', 'isPromo', 'description', 'text', 'link', 'date'] 
# rename_cols = ['sku', 'product_id', 'color_id', 'color', 'fit', 'final_price', 'original_price', "headline", 'cotton', 'polyester', 'spandex', 'modal', 'elastomultiester', 'is_promo', 'description', 'text', 'link', 'date'] 

# renaming some columns
selected_cols = ['finalPrice', 'originalPrice', 'isPromo'] 
rename_cols = ['final_price', 'original_price', 'is_promo'] 

final_cols = dict(zip(selected_cols, rename_cols))
df_final.rename(columns = final_cols, inplace = True )

# converting all columns to lower case
original_col = list(df_final.columns)
lower_col = [col.lower() for col in original_col]
final_cols = dict(zip(original_col, lower_col))

df_final.rename(columns = final_cols, inplace = True )

df_final.head()
### Converting Data Types
# converting dtypes to numeric
df_final.dtypes
# fill NAs
df_final.isna().sum()

df_final.fillna(0, inplace = True)

# selects all numerical columns
cols_to_num = list(df_final.columns)
str_cols = ['sku','product_id','color_id', 'color', 'fit', 'price', 'final_price', 'original_price', 'headline', 'description', 'composition', 'comp', 'lining', 'text', 'link', 'date']
for col in str_cols:
    cols_to_num.remove(col)

cols_to_num
print(cols_to_num)

for col in cols_to_num:
    try:
        # convert to float then to int (to avoid NA to int error)
        df_final[col] = df_final[col].astype(int)
    except:
        df_final[col] = df_final[col].astype('Int64')
    finally:
        pass

# converting date to datetime
df_final['date'] = pd.to_datetime( df_final['date'], errors = 'coerce')
df_final.dtypes
# Data Saving
## Saving Locally
# dropping unnecessary columns 

df_final.drop(['price', 'composition', 'comp'], axis = 1, inplace = True)
# Saving Locally
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# saving df as a local backup
df_final.to_csv('../backups/df_backup-{}.csv'.format(now), index = False)

print('saved: df_backup-{}.csv'.format(now))
df_final.dtypes
# # Inserting processed data into MySQL DB
# # path = 'sqlite:///' + path_to_db
# path = 'sqlite:///' + '/home/humberto/DS/hm/jeans_db.sqlite'
# # creating sqlalchemy engine for connection
# engine = create_engine(path, echo=True)

# # creating a Session class
# Session = sessionmaker(bind=engine)

# # creating a session
# session = Session()
# # testing case a new column is added
# try:
#     # adding data
#     df_final.to_sql('hm_showroom2', con = engine, if_exists='append', index = False)

#     # committing changes
#     session.commit()
# except:
#     try:
#         # in case scraped data returns with a new column, it will be added to a new table
#         table_name = "hm_showroom_backup-{}".format(datetime.now().strftime("%Y-%m-%d"))
#         df_final.to_sql( table_name, con = engine, if_exists='append', index = False)

#         session.commit()
#     except:  
#         # if even this fails, undo everything      
# # df_comp.to_csv(path_or_buf='./backups/df_comp-{}.csv'.format(now), index = False )
#         session.rollback()

# finally:
#     session.close()

# # USE THIS SCRIPT TO PREVENT FAILS
## Inserting data to MySQL on AWS
# reading credentials

secrets_json = open('./secrets/secrets.json')
secrets = json.load(secrets_json)

dialect =   secrets["dialect"]
driver =    secrets["driver"]
host =      secrets["host"]
username =  secrets["username"]
password =  secrets["password"]
port =      secrets["port"]
database =  secrets["database"]

url = "{}+{}://{}:{}@{}:{}/{}".format(dialect, driver, username, password, host, port, database)
# engine = create_engine(url = url, echo = True) #, pool_pre_ping = True
# Inserting processed data into MySQL DB

# creating sqlalchemy engine for connection
engine = create_engine(url, echo=True)

# creating a Session class
Session = sessionmaker(bind=engine)

# creating a session
session = Session()
# testing case a new column is added

try:
    # adding data
    df_final.to_sql('hm_showroom', con = engine, if_exists='append', index = False)

    # committing changes
    session.commit()
except:
    try:
        # in case scraped data returns with a new column, it will be added to a new table
        table_name = "hm_showroom_backup-{}".format(datetime.now().strftime("%Y-%m-%d"))
        df_final.to_sql( table_name, con = engine, if_exists='append', index = False)

        session.commit()
    except:  
        # if even this fails, undo everything      
        session.rollback()

finally:
    session.close()

# USE THIS SCRIPT TO PREVENT FAILS
session.close()