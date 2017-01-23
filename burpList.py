####################################Burp Suite Custom Wordlist######################################
##Creates a wordlist from the current context of the right click menu within burp, from the target##
##tab, right click on a HTML request and select 'Custom Wordlist' this will create a file for all ##
##unique words present on the web page.  Enjoy :^)                                                ##
####################################################################################################
#Thanks to Black Hat Python, and #HackersWithoutBorders

#itsa me
__author__ = 'Patrick Grech'

# burp imports
from burp import IBurpExtender #required for burp to burp
from burp import IContextMenuFactory  # right click functionality

# python imports
from bs4 import BeautifulSoup  # pull html data
import json
import re
import string

# java imports
from java.awt import BorderLayout

from javax.swing import JMenuItem
from javax.swing import JFileChooser
from java.util import List, ArrayList
from javax.swing.filechooser import FileNameExtensionFilter
from javax.swing import JPanel
from javax.swing import BorderFactory
from javax.swing import JScrollPane
from javax.swing import JFrame
from javax.swing import JTextArea

class BurpExtender(IBurpExtender,IContextMenuFactory,JFrame):
    def registerExtenderCallbacks(self, callbacks):
        print '------------------------------Welcome to the Burp Suite Wordlist Creator----------------------------------'
        print 'Right click HTML or JSON responses in the Target tab to gather all unique words gathered from the response'
        # print '##########################################################################################################'
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self.context = None
        self.hosts = set()

        #Define extension properties
        callbacks.setExtensionName("Custom Wordlist")
        callbacks.registerContextMenuFactory(self)

        #wordlist file
        self.wordlist = []

        #Setup space for save dialogue to sit in.
        self.panel = JPanel()
        self.panel.setLayout(BorderLayout())

        self.area = JTextArea()
        self.area.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))

        pane = JScrollPane()
        pane.getViewport().add(self.area)

        self.panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))
        self.panel.add(pane)
        self.add(self.panel)

        self.setTitle("File chooser")
        self.setSize(300, 250)
        self.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE)
        self.setLocationRelativeTo(None)
        #this is just providing a place where the save box can sit in, no need for it to be visible on start
        self.setVisible(False)
        return

    def createMenuItems(self, context_menu):
        self.context = context_menu
        menu_list = ArrayList()
        #gather the information that is right-clicked
        menu_list.add(JMenuItem("Custom Wordlist", actionPerformed=self.wordlistCreate))

        return menu_list

    def wordlistCreate(self,event):
        #gathers information from the context menu, can be perused through with getResponse()
        http_traffic = self.context.getSelectedMessages()
        #empty the list so concurrent lists don't get mixed up
        self.wordlist = []
        hosts = ''
        #thanks BHP
        for traffic in http_traffic:
            http_service = traffic.getHttpService()
            hosts = http_service.getHost()
            #gathers all responses from the traffic
            http_response = traffic.getResponse()

            if http_response:
                words = self.handleTraffic(http_response)
                #add a list to the wordlist
                self.wordlist.extend(words)
            else:
                continue
        #after all words have been added, write to file
        self.filewrite(hosts)

    def handleTraffic(self,http_response):
        print '#######################################Creating Wordlist...###############################################'
        headers, body = http_response.tostring().split('\r\n\r\n', 1)
        soup = BeautifulSoup(body, "html.parser")
        w_list = []

        #To look for more headers, add content-type

        #if the content is not JSON
        if headers.lower().find("content-type: application/json") == -1:
            w_list = self.workwithhtml(soup)
        elif headers.lower().find("content-type: application/json"):
            w_list = self.workwithjson(body)
        return w_list

    def workwithhtml(self,soup):
        #values to be added to the wordlsit
        w_list = []
        #list of numbers found larger than 4 characters
        numbers = []
        #strip tags from content (only gather text)
        [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title', 'nav'])]

        #soup output has to be encoded
        words = soup.get_text().encode('utf-8')
        #encode wordlist with ascii, replacing unknown chars with '?' which will be stripped later on. Solves issues with the ' character as a result of a failed encoding
        words = words.encode('ascii','replace')

        #sub all special chars with blank space
        bad_chars = re.escape(string.punctuation)
        bad_chars = bad_chars.replace("\'", "")

        #split on whitespace
        for w in words.split(" "):
            #strip new lines
            w = w.strip('\n')
            #replace all new lines
            w = w.replace("\n", "")
            numbers = self.numspresent(w,numbers)
            w_list = self.addtolist(w,w_list,bad_chars)

        #if there are no numbers greater than 4 chars
        if not numbers:
            print 'No interesting numbers found.'
        else:
            print 'Potentially interesting number for mangling:'
            #print all interesting numbers found
            for i in numbers:
                print i
        return w_list

    def workwithjson(self,body):
        #values to be added to the wordlist
        jList = []
        #list of numbers found larger than 4 characters
        numbers = []
        json_data = json.loads(body)

        #sub special chars with blank space
        bad_chars = re.escape(string.punctuation)
        bad_chars = bad_chars.replace("\'", "")

        for key, w in json_data.items():

            #check for numbers
            numbers = self.numspresent(key,numbers)
            numbers = self.numspresent(w,numbers)

            #handle the key and value for Json Data
            jList = self.addtolist(key,jList,bad_chars)
            jList = self.addtolist(w,jList,bad_chars)
        if not numbers:
            print 'No interesting numbers found.'
        else:
            print 'Potentially interesting number for mangling:'
            #print all interesting numbers found
            for i in numbers:
                print i
        return jList

    #check if there are numbers present in the value, if there are, add to list to be printed later.
    def numspresent(self,value,numbers):
        if len(value) >= 4 and value.isdigit():
            if value in numbers:
                pass
            else:
                numbers.append(value)
                w = ''
        return numbers

    def addtolist(self,value,wList,bad_chars):
        # bad_chars instantiated further up, essentially a list of special chars apart from '
        stripchars = re.sub(r'['+bad_chars+']', '', value)
        #strip numbers from value, nums already found.
        value = re.sub('[0-9]', '', stripchars)
        #grab strings that are of a reasonable length
        if len(value) >= 3 and len(value) < 12:
            value = self.checkforcontraction(value)
            wList.append(value.strip().lower())
        return wList

    def checkforcontraction(self,value):
        if "'" in value:
            if "'s" in value:
                pass
            elif "n't" in value:
                pass
            elif "'v" in value:
                pass
            elif "'r" in value:
                pass
            elif "'l" in value:
                pass
            elif "s'" in value:
                pass
            else:
                value = value.replace("'","")
        return value

    def filewrite(self,hosts):
        print 'Preparing wordlist for the host: '+hosts
        print '##########################################################################################################'
        wlist = list(set(self.wordlist))
        self.promptuser(wlist)


    def promptuser(self,wlist):
        fileChooser = JFileChooser()
        filter = FileNameExtensionFilter("Text Files",["txt"])
        #shows only text files in the save menu prompt
        fileChooser.setFileFilter(filter)

        ret = fileChooser.showSaveDialog(self.panel)
        #if they have selected the save option
        if ret == JFileChooser.APPROVE_OPTION:
            file = fileChooser.getSelectedFile()
            #get the path that the user selected
            filepath = str(file.getCanonicalPath())

            with open(filepath, 'a+') as f:
                for word in sorted(wlist):
                    if word == '':
                        pass
                    else:
                        f.write(word +'\n')
            print 'Wordlist created at '+filepath
            print '##########################################################################################################\n'