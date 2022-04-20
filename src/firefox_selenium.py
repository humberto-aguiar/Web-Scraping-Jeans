from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# starting drive
options = Options()
options.headless = True
driver = webdriver.Firefox(options=options)

driver.get("https://www2.hm.com/en_us/productpage.0811993021.html")
class_ = "ProductDescription-module--descriptionText__1zy9P"

content = WebDriverWait(driver, 10).until(EC.presence_of_element_located( (By.CLASS_NAME, class_) ))
desc = content.text
print(desc)