##
## author - Simone Marchi (simone.marchi@ilc.cnr.it)
##
import requests
from bs4 import BeautifulSoup
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import getopt, sys, os
import logging

logger = logging.getLogger('GYsearch')

def usage():
    print ("""usage: python {} -w|--word word_to_search
    \t-s|--site (e.g. www.python.org)
    \t-u|--inurl string  (e.g. resources)
    \t-l|--limit integer (max number of result)
    \t-n|--nodownload (show only retrieved link)
    \t-f|--filetype string (e.g. doc, docx, pdf etc.)
    \t-o|--outputdir string (output_directory)
    \t-d|--debug integer (0: not set, 10: debug, 20: info, 30: warning, 40: error, 50: critical)
    \t Example: python {} -w test --site www.ibm.com  --filetype pdf -l 3""".format(sys.argv[0],sys.argv[0]))
    sys.exit()

def downloadResource(url):
    try:
        document = requests.get(url, allow_redirects=True) #retrieve the document refered by url
        return document.content
    except  requests.exceptions.RequestException as e:
        logger.error("Error retrieving document {}".format(url))
        return None

def saveResource(outputDir, url, word, resourceContent):
    path = outputDir+'/'+'/'.join(url.split('/')[2:-1]) #build the output path for the retrieved file
    resourceName = url.rsplit('/', 1)[-1] #get the filename (last part of url)
    logger.debug ("ResourceName {}".format(resourceName))
    if not resourceName:
        logger.debug("resourceName is empty, set to {}".format(word)) #the filena doesn't exist, use the searched word instead
        resourceName = word
    os.makedirs(path,exist_ok=True)

    filename = "{}/{}".format(path,resourceName)
    logger.debug("Filename: {}".format(filename))

    fo = open(filename, 'wb')
    fo.write(resourceContent)
    fo.close()

def main():

    step = 1
    previous_page = None #previous results page
    SE = None #the search engine selected
    listOfSE = ["yahoo","google"]
    listOfFiletype = ["doc","pdf","docx"]
    word = None #serched word
    outputDir = None
    filetype = None
    site = None
    inurl = None
    download = True
    limit = 0
    searchUrl = None
    logLevel = 20 #INFO
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   'w:o:f:s:e:u:nl:hd:',
                                   ["word=", "output=",
                                    "filetype=", "site=", "engine="
                                    "inurl=","nodownload",
                                    "limit=","help","debug="])
    except getopt.GetoptError as e:
        print("Error parsing arguments: {}".format(e))
        usage()

    #Set up the logging system
    logFormatter = logging.Formatter(fmt=' %(asctime)s :: %(name)s :: %(levelname)-8s :: %(message)s',
                                     datefmt='%d.%m.%y %H:%M:%S')
    consoleHandler = logging.StreamHandler(sys.stderr)
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        if o in ("-w", "--word"):
            word = a
        elif o in ("-o", "--output"):
            outputDir = a
        elif o in ("-f", "--filetype"):
            if a in listOfFiletype:
                filetype = a
            else:
                print("Invalid filetype {}".format(a))
        elif o in ("-s", "--site"):
            site = a
        elif o in ("-e", "--engine"):
            if a in listOfSE:
                SE = a
            else:
                print("Invalid search engine name: {}, using Google".format(a))
                SE = "google"
        elif o in ("-u", "--inurl"):
            inurl = a
        elif o in ("-n", "--nodownload"):
            download = False
        elif o in ("-l", "--limit"):
            try:
                limit = int(a)
            except ValueError as ve:
                print("Error {}".format(ve))
        elif o in ("-d", "--debug"):
            try:
                logLevel = int(a)
                if (logLevel not in [0, 10, 20, 30, 40, 50]):
                    raise ValueError("Log level must be: 0, 10, 20, 30, 40 or 50")
            except ValueError as ve:
                print("Error: {}".format(ve))
                usage()
        else:
            assert False, "unhandled option"

    logger.setLevel(logLevel)

    if limit == 0:
        limit = 10
        logger.info("Limit search results to one page only.")
    if SE is None:
        logger.info("Using Google as search engine")
        SE = "google"

    if word is None:
        logger.error("Word to search is mandatory [-w]")
        usage()

    if outputDir is None:
        logger.info("Output director is set to {}".format(word))
        outputDir = word #the output path start with the searched word
    else:
        if word[-1] != '/':
            outputDir += '/'
        outputDir += word

    chrome_options = Options()
    chrome_options.add_argument("--headless") #hidden browser
    driver = webdriver.Chrome(options=chrome_options) #create browser instance
    driver.implicitly_wait(30)

    if SE == "yahoo":
        searchUrl = "https://search.yahoo.com/search?p='" + word +"'"
    elif SE == "google":
        searchUrl = "https://www.google.com/search?q=\"" + word + "\""
    if site != None:
        searchUrl += "+site:" + site
    if filetype != None:
        searchUrl += "+filetype:" + filetype

    logger.info("SearchUrl: {}".format(searchUrl))

    logger.debug("Limit is {}".format(limit))
    while (step <= limit):
        driver.get(searchUrl)
        if step == 1: #first call
            try:
                logger.debug("Set up the first call")
                wait = WebDriverWait(driver, 5)
                button = None #cookies acceptance button
                if SE == "yahoo":
                    button = '//button[@name="agree"]'
                elif SE == "google":
                    button = '//button[@id="L2AGLb"]'
                wait.until(EC.element_to_be_clickable((By.XPATH, button)))
                #looking for cookie acceptance button and click it
                driver.find_element(By.XPATH,button).click()
                logger.debug("Set up completed")
            except TimeoutException as te:
                logger.error(te)

        if previous_page != driver.page_source:
            logger.debug("Set up BeautifulSoup")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            if SE == "yahoo":

                links = soup.find_all(class_=re.compile('tc va-bot mxw-100p'))

                if links == []:
                    logger.warning("No results found. It should be a problem with soup.find_all!")

                for link in links:
                    resourceRef = link.get('href')
                    logger.info("Y: {}".format(resourceRef))
                    if(download):
                        resourceContent = downloadResource(resourceRef)
                        if resourceContent is not None:
                            saveResource(outputDir, resourceRef, word, resourceContent)
                            logger.debug("Resource saved")
                        else:
                            logger.warning("Unable to retrieve {}".format(resourceRef))

                next = soup.find(class_="next",href=True)['href']
                logger.debug("next page {}".format(next))
                searchUrl = next
                step += 7 #yahoo default number of results in a page
            elif SE == "google":
                special_divs = soup.find_all('div',{'class':'yuRUbf'})
                for div in special_divs:
                    anchors = div.find_all('a')
                    for anchor in anchors:
                        resourceRef = (anchor['href'])
                        logger.info("G: {}".format(resourceRef))
                        if "webcache" in  resourceRef or "related" in resourceRef:
                            print("Problem with Google webcache", resourceRef)
                            continue
                        #download della risorsa
                        if(download):
                            resourceContent = downloadResource(resourceRef)
                        if resourceContent is not None:
                            saveResource(outputDir, resourceRef, word, resourceContent)
                            logger.debug("Resource saved")
                        else:
                            logger.warning("Unable to retrieve {}".format(resourceRef))

                try:
                    next = soup.find(id="pnnext",href=True)['href']
                    logger.debug("G next result page {}".format(next))
                    searchUrl = "https://www.google.com" + next #URL for the next result page
                except TypeError as e:
                    print("No more results")
                    break
                step += 10
            logger.info("Next SearchUrl: {}".format(searchUrl))
            previous_page = driver.page_source

        else:
            break
    driver.quit()


if __name__ == '__main__':
    main()
