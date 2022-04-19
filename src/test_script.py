from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# instatiate driver
options = Options()
options.headless = True
driver = webdriver.Firefox(options=options)

# request elements
## Product Description
driver.get("https://www2.hm.com/en_us/productpage.0811993021.html")
# class_ = "BodyText-module--general__32l6J" # if below doesn't work
class_ = "ProductDescription-module--descriptionText__1zy9P"

try: 
    content = WebDriverWait(driver, 10).until(EC.presence_of_element_located( (By.CLASS_NAME, class_) ))
    desc = content.text
except:
    desc = 'NA'

content = WebDriverWait(driver, 10).until(EC.presence_of_element_located( (By.CLASS_NAME, class_) ))
desc = content.text


## Text
elements = driver.find_elements(by=By.CLASS_NAME, value="ProductAttributesList-module--descriptionListItem__3vUL2")
# elements = elements.text
text = str()
text = [text + line.text  for line  in elements]
# text

# joining everything to save as raw text
text_raw =' /'.join(text)
text_raw
# searching for words fit and composition in all text retrieved from products web page
for element in text:
    if 'fit' in element:
        fit = element
    if 'Composition' in element:
        composition = element
## Price
class_price = "ProductPrice-module--productItemPrice__2i2Hc"
element = WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CLASS_NAME, class_price) ) )
price = element.text

# if element returns empty, try this other class
if element.text == '':
    class_price = "price.parbase"
    element = WebDriverWait(driver, 10).until( EC.presence_of_element_located( (By.CLASS_NAME, class_price) ) )
    price = element.text
    
    if price == '':
        price = 'NA'

# print results
print('Description: ',desc)

print('Texts: \n')
for e in text:
    print(e)

print('\nFit: ', fit)
print('Composition: ', composition)