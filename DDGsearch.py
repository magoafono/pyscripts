##
## author - Simone Marchi (simone.marchi@ilc.cnr.it)
##
import requests
import os
import getopt, sys
import logging
import time
from duckduckgo_search import ddg


def usage():
    print ("""usage: python {} -w|--word word_to_search
    \t-s|--site (e.g. www.python.org)
    \t-u|--inurl string  (e.g. download)
    \t-l|--limit integer (max number of results)
    \t-n|--nodownload (show only retrieved link)
    \t-f|--filetype string (e.g. doc, docx, pdf etc.)
    \t-o|--outputdir string (output_directory)
    \t-d|--debug integer (0: not set, 10: debug, 20: info, 30: warning, 40: error, 50: critical)
    \t Example: python {} -w test --site www.ibm.com  --filetype pdf -l 3""".format(sys.argv[0],sys.argv[0]))
    sys.exit()

#Example of invocation
#python ddg.py -w דת --site fs.knesset.gov.il --filetype doc
def main():

    word = None #word to search
    outputDir = None #output directory to save download files
    filetype = None #file type to search
    site = None #restrict searches to a specific site
    inurl = None #restrict searches to a subdomain
    download = True #download document after search
    limit = 10 #max nomber of document retrieved
    logLevel = 20 #log level set to INFO

    opts, args = getopt.getopt(sys.argv[1:],
                               'w:o:f:s:u:nl:d:h',
                               ["word=", "output=",
                                "filetype=", "site=",
                                "inurl=","nodownload",
                                "limit=","debug","help"])

    #Set up the logging system
    logger = logging.getLogger('DDGsearch')
    logFormatter = logging.Formatter(fmt=' %(asctime)s :: %(name)s :: %(levelname)-8s :: %(message)s',
                                     datefmt='%d.%m.%y %H:%M:%S')
    consoleHandler = logging.StreamHandler(sys.stderr)
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)

    logger.debug("Arguments {}".format(sys.argv[1:]))

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        if o in ("-w", "--word"):
            word = a
        elif o in ("-o", "--output"):
            outputDir = a
        elif o in ("-f", "--filetype"):
            filetype = a
        elif o in ("-s", "--site"):
            #print("You cannot set site. Search only in",site)
            site = a
        elif o in ("-u", "--inurl"):
            inurl = a
        elif o in ("-n", "--nodownload"):
            download = False
        elif o in ("-l", "--limit"):
            try:
                limit = int(a)
            except ValueError as ve:
                print("Limit is not an integer: {}".format(limit))
                usage()
        elif o in ("-d", "--debug"):
            try:
                logLevel = int(a)
                if (logLevel not in [0, 10, 20, 30, 40, 50]):
                    raise ValueError("Log level must be: 0, 10, 20, 30, 40 or 50")
                logger.setLevel(logLevel)
            except ValueError as ve:
                print("Error: {}".format(ve))
                usage()
        else:
            assert False, "unhandled option"

    logger.setLevel(logLevel)

    if word is None:
        print ("Error: The chose of a word is mandatory [-w]")
        usage()

    if outputDir is None:
        outputDir = word #the output path strat with the searched word
    else:
        if word[-1] != '/':
            outputDir += '/'
        outputDir += word

    searchString = word

    if filetype is not None:
        searchString +=  ' filetype:' + filetype
    else:
        logger.debug("No filetype specified")

    if site is not None:
        searchString += ' site:' + site
    else:
        logger.debug("No site specified")

    if inurl is not None:
        searchString += ' inurl:' + inurl
    else:
        logger.debug("No inurl specified")

    logger.info("Search string: {} ".format(searchString))

    results = None

    try:
        results = ddg(searchString, region='wt-wt', safesearch='Off', max_results=limit)
    except Exception as ex:
        logger.error("Error retrieving results {}".format(ex));

    if results != None:
        logger.info ("Number of results: {}".format(len(results)))

        for result in results:

            url = result["href"]

            logger.info("URL: {}".format(url))

            if(download):
                r = requests.get(url, allow_redirects=True) #retrive the document refered by url
                path = outputDir+'/'+'/'.join(url.split('/')[2:-1]) #build the output path for the retrieved file
                filename = url.rsplit('/', 1)[-1] #get the filename (last part of url)
                logger.debug("filename: " + filename)
                if not filename:
                    logger.warning("filename is empty") #the filename doesn't exist, use the searched word instead
                    filename = word
                os.makedirs(path,exist_ok=True)

                logger.debug("Saving {}".format(path+'/'+filename))

                fo = open(path+'/'+filename, 'wb')
                fo.write(r.content)
                fo.close()
            else:
                logger.info("Entry: {}".format(url))
    else:
        print("No results.")

if __name__ == '__main__':
    main()
