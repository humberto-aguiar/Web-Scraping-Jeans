#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 20 16:47:30 2021

@author: humberto
"""
def request_soup(url_link):    
    headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'}    
    page = requests.get( url, headers = headers)
    soup_obj = BeautifulSoup(page.text, 'html.parser')
    return( soup_obj )

#import logging
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import re
from sqlalchemy import create_engine
import sqlite3

# ==============
# Buscar ID de todos os produtos
# ==============

url = 'https://www2.hm.com/en_us/men/products/jeans.html'
headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'}

page = requests.get( url, headers = headers)
soup = BeautifulSoup(page.text, 'html.parser')

p = soup.find('div', class_='load-more-products')
total_items = int( soup.find('h2', class_='load-more-heading').get('data-total') )

total_pages = np.ceil( total_items/36 )

url_total = url + '?&offset=0&page-size=' + str( int( total_pages*36 ) )

page_total = requests.get( url_total, headers = headers)
soup_total = BeautifulSoup( page_total.text, 'html.parser')

# List with all products in page
products = soup_total.find( 'ul', class_="products-listing small") #tag element
product_list = products.find_all( 'article', class_='hm-product-item')

link = [ 'https://www2.hm.com/' + item.find('a').get('href') for item in product_list ]

# Buscar caracts de cada um dos produtos
color_aux = pd.DataFrame()

cols = ['Art. No.', 'Composition', 'Fit', 'Size']

# Color Scraping

for url in link:
    soup = request_soup(url)
    
    #color search    
    colors_list = soup.find('ul', class_="inputlist clearfix")
    colors = [ elements.get('data-color') for elements in colors_list.find_all('a', ["filter-option miniature active", "filter-option miniature"]) ]
    
    color_id = [ element.get('data-articlecode') for element in colors_list.find_all('a',  ["filter-option miniature active", "filter-option miniature"] ) ]
    color_id
    color = pd.DataFrame( [ color_id, colors] ).T
    print(color)
    color.columns = ['Art. No.' , 'color' ]

    print('Queried ID: ', str(color['Art. No.'][0])  )
    color_aux = pd.concat( [color_aux, color], axis = 0 )
    color = pd.DataFrame()
     
color = color_aux.drop_duplicates().copy()
color['style_id'] = color['Art. No.'].apply( lambda x: x[:-3] )
color['color_id'] = color['Art. No.'].apply( lambda x: x[-3:] )
color['link'] = color['Art. No.'].apply( lambda x: 'https://www2.hm.com/en_us/productpage.' + str(x) + '.html')

# Composition Scraping
comp_aux = pd.DataFrame()    

for url_comp in color['link']:
    #comp_soup = request_soup(url_comp)    
    r3 = requests.get(url = url_comp, headers = headers)
    comp_soup = BeautifulSoup(r3.text, 'html.parser')   
        
    # Search for composition
    attr = comp_soup.find_all( 'div', class_="pdp-description-list-item" )
    pdp_desc = [ list(filter( None, item.text.split('\n') ) ) for item in attr ]
    prod = pd.DataFrame( pdp_desc ).T
    prod.columns = prod.iloc[0,:]
    prod = prod.iloc[1: , :]
    
    #Concatenate composition
    comp = ''
    for i in range(len(prod)):
        if not prod.Composition.iloc[i] == None:
            comp += prod.Composition.iloc[i] + ' '

    prod['Composition'] = comp
    prod.dropna(inplace=True)

    # Finding Price
    comp_soup.find_all( 'div', class_="pdp-description-list-item" )
    a = str(comp_soup.find_all( 'div', class_="primary-row product-item-price")[0])
    prod['Price'] = re.findall('\$\d*.\d*', a)[0].strip('$')
    
    comp_aux = pd.concat( [comp_aux, prod[['Fit', 'Composition', 'Art. No.','Price']] ], axis = 0 ) #, inplace = True
    print( 'Queried comp ID: ', str( url_comp[39:49] ) )    
    comp_aux['date'] = datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )

#color.nunique()

#df = color.merge( comp_aux, on = 'Art. No.', how = 'right' )

df = pd.merge( color, comp_aux, on = 'Art. No.', how = 'inner')

#sku.to_csv('sku_df.csv')

texts = []
for text in df['Composition']:
    if 'Pocket' in text:
        regex = '(Shell: .* Pocket|Shell.*%|Cotton.* Pocket|% Cotton.*)'
        texts.append(re.findall( regex, text)[0])
    else:
        regex = '(Cotton.*Lining|Cotton.*%)'
        texts.append(re.findall( regex, text)[0])

df['texts'] = texts
df_comp = df[['Composition', 'texts']].copy()
df_comp[[ 'Cotton', 'Polyester', 'Elastane', 'Elasterell-P', 'Modal', 'Viscose' ]] = 0

for row in range(len( df_comp) ):
    text = str( df_comp.loc[row,'texts'])
    cotton_res = re.findall( 'Cotton [0-9]*%' , text)
    poly_res = re.findall( 'Polyester [0-9]*%' , text)
    elas_res = re.findall( 'Elastane [0-9]*%' , text)
    elasrell_res = re.findall( 'Elasterell-P [0-9]*%' , text)
    modal_res = re.findall( 'Modal [0-9]*%', text)
    visc_res = re.findall( 'Viscose [0-9]*%', text)
    
    if cotton_res:
        df_comp.loc[ row, 'Cotton'] = int(cotton_res[0].split()[1].strip('%')) 
    if poly_res:
        df_comp.loc[ row, 'Polyester'] = int(poly_res[0].split()[1].strip('%')) 
    if elas_res:
        df_comp.loc[ row, 'Elastane'] = int(elas_res[0].split()[1].strip('%')) 
    if elasrell_res:
        df_comp.loc[ row, 'Elasterell-P'] = int(elasrell_res[0].split()[1].strip('%')) 
    if modal_res:
        df_comp.loc[ row, 'Modal'] = int(modal_res[0].split()[1].strip('%')) 
    if visc_res:
        df_comp.loc[ row, 'Viscose'] = int(visc_res[0].split()[1].strip('%')) 

df = pd.concat( [df, df_comp.iloc[:,2:]], axis = 1 )

date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') #
df.to_csv('./df_comp-' + str(date_time) + '.csv', index = False)

df_insert = df[['Art. No.', 'style_id', 'color_id',  'color', 'Fit',
 'Price', 'Composition','texts', 'Cotton', 'Polyester', 
 'Elastane', 'Elasterell-P', 'Modal', 'Viscose', 'link', 'date']].copy()

# creating database
con = sqlite3.connect('hm_db.sqlite')

# connecting to database
conn =  create_engine( 'sqlite:///hm_db.sqlite', echo = True)

#inserting table to db
df_insert.to_sql( 'showroom', con = conn, if_exists= 'append', index = False )

# checking data
query = """
    SELECT * FROM showroom
"""
df_read = pd.read_sql_query( query, conn )

# execute query
#query_drop = """
#    DROP TABLE showroom
#""" 
#con = sqlite3.connect('hm_db.sqlite')
#cursor = con.execute( query_drop )
#con.commit()
#con.close()