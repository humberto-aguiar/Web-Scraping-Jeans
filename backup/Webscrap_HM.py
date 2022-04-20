# -*- coding: utf-8 -*-
"""
Created on Mon Aug 23 16:18:45 2021

@author: humberto
"""
# Imports

import pandas as pd
import numpy as np
import requests
import re
import sqlite3
import logging
import os
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
   

def product_links( url, headers ):        
    # ==============
    # Buscar ID de todos os produtos
    # ==============
    page = requests.get( url, headers = headers)
    soup = BeautifulSoup(page.text, 'html.parser')
    
   # p = soup.find('div', class_='load-more-products')
    total_items = int( soup.find('h2', class_='load-more-heading').get('data-total') )
    
    total_pages = np.ceil( total_items/36 )
    
    url_total = url + '?&offset=0&page-size=' + str( int( total_pages*36 ) )
    
    page_total = requests.get( url_total, headers = headers)
    soup_total = BeautifulSoup( page_total.text, 'html.parser')
    
    # List with all products in page
    products = soup_total.find( 'ul', class_="products-listing small") #tag element
    product_list = products.find_all( 'article', class_='hm-product-item')
    
    link = [ 'https://www2.hm.com/' + item.find('a').get('href') for item in product_list ]
    return link


##

def get_products_data( link, headers ):

    # Color Scraping
    
    color_aux = pd.DataFrame()
    
    for url in link:
        
        page = requests.get( url, headers = headers)
        soup = BeautifulSoup(page.text, 'html.parser')
        
        #color search    
        colors_list = soup.find('ul', class_="inputlist clearfix")
        colors = [ elements.get('data-color') for elements in colors_list.find_all('a', ["filter-option miniature active", "filter-option miniature"]) ]
        
        color_id = [ element.get('data-articlecode') for element in colors_list.find_all('a',  ["filter-option miniature active", "filter-option miniature"] ) ]
        color_id
        color = pd.DataFrame( [ color_id, colors] ).T
        color.columns = ['Art. No.' , 'color' ]
    
        logger.debug( 'Queried link: %s', url )
        color_aux = pd.concat( [color_aux, color], axis = 0 )
        color = pd.DataFrame()
 
    color = color_aux.drop_duplicates().copy()
    color['style_id'] = color['Art. No.'].apply( lambda x: x[:-3] )
    color['color_id'] = color['Art. No.'].apply( lambda x: x[-3:] )
    color['link'] = color['Art. No.'].apply( lambda x: 'https://www2.hm.com/en_us/productpage.' + str(x) + '.html')
    
    # Composition Scraping
    comp_aux = pd.DataFrame()    
    
    for url_comp in color['link']:
        try:
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
        
            # Price Search
            comp_soup.find_all( 'div', class_="pdp-description-list-item" )
            a = str(comp_soup.find_all( 'div', class_="primary-row product-item-price")[0])
            prod['Price'] = re.findall('\$\d*.\d*', a)[0].strip('$')
            
            comp_aux = pd.concat( [comp_aux, prod[['Fit', 'Composition', 'Art. No.','Price']] ], axis = 0 ) #, inplace = True
            print( 'Queried comp ID: ', str( url_comp[39:49] ) )    
            comp_aux['date'] = datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
            logger.debug( 'Queried attr for: %s', url_comp )
        except Exception as err:
            logger.error( err )        
            pass
            
    df = pd.merge( color, comp_aux, on = 'Art. No.', how = 'inner')
    return df
    
def data_cleaning(df):
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
    return df

def data_insert(df):
    df_insert = df[['Art. No.', 'style_id', 'color_id',  'color', 'Fit',
     'Price', 'Composition','texts', 'Cotton', 'Polyester', 
     'Elastane', 'Elasterell-P', 'Modal', 'Viscose', 'link', 'date']].copy()
    
    # creating database
    con = sqlite3.connect('/home/humberto/DS/DSaoDEV/hm/hm_db.sqlite')
    con.close()
    #con = sqlite3.connect('hm_db.sqlite')
    # connecting to database
    conn =  create_engine( 'sqlite:////home/humberto/DS/DSaoDEV/hm/hm_db.sqlite', echo = True)
    
    #inserting table to db
    df_insert.to_sql( 'showroom', con = conn, if_exists= 'append', index = False )
    if not ( os.path.exists('/home/humberto/DS/DSaoDEV/hm/backups/') ):
        os.mkdir('/home/humberto/DS/DSaoDEV/hm/backups/')
    savepath = '/home/humberto/DS/DSaoDEV/hm/backups/df_backup-' + datetime.now().strftime( '%Y-%m-%d_%H:%M:%S') + '.csv'
    df_insert.to_csv( savepath, index = False )
    


# checking data
#    query = """
#        SELECT * FROM showroom
#    """
#    df_read = pd.read_sql_query( query, conn )
#    
    
#    query = """
#        CREATE TABLE test(
#        ID INT
#        )
#    """
#    cursor = con.execute( query )
#    cursor.comit()
    # execute query
    #query_drop = """
    #    DROP TABLE showroom
    #""" 
    #con = sqlite3.connect('hm_db.sqlite')
    #cursor = con.execute( query_drop )
    #con.commit()
    #con.close()
    return None

if __name__ == '__main__' :
    # Logging
    path = '/home/humberto/DS/DSaoDEV/hm/' 
    if not ( os.path.exists( path + 'logs' ) ):
        os.mkdir( path + 'logs' )
    
    
    logging.basicConfig( filename = path + '/logs/hm_logs.log',
                       format =  '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                       datefmt = '%Y-%m-%d %H:%M:%S',
                       level = logging.DEBUG )
    logger = logging.getLogger( 'webscraping_hm' )
    
    logger.debug('STARTING WEB SCRAPING')
    #Parameters and Constants
    url = 'https://www2.hm.com/en_us/men/products/jeans.html'
    #headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0'}
    #headers = {'User-Agent' : 'Opera/9.80 (X11; Linux i686; U; ru) Presto/2.8.131 Version/11.11 ua.chrome'}    
    headers =  {'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2919.83 Safari/537.36' }

    # Product collection from HM Web_site
    try:
        link = product_links( url, headers)
        logger.info( 'Product links collection done' )
    except Exception as err :
        logger.error( err )
    
    # Web Scraping
    try:
        df = get_products_data( link, headers )
        logger.info( 'Products webscraping done' )
    except Exception as err :
        logger.error( err )
    
    # Data Cleaning
    try: 
        df = data_cleaning( df )
        logger.info( 'Data cleaning done' )
    except Exception as err :
        logger.error( err )
    
    # Data Base Inserting
    try: 
        data_insert( df )
        logger.info( 'Database update done' )
    except Exception as err :
        logger.error( err )    
