'''
Created on May 13, 2017

@author: guido
'''

from __future__ import print_function
from cmd import Cmd
import time
import pychromecast
from WebServer import WebServerClass
from instagram.client import InstagramAPI

class MyPrompt(Cmd):

    WebS = None
    
    def do_startWeb(self, args):
        if len(args) == 0:
            folder = 'demo-test'
        else:
            folder = args

        if self.WebS is None:
            self.WebS = WebServerClass(folder)
        
        if not self.WebS.isRunning():
            self.WebS.startServingRequests()
    
    def do_stopWeb(self, args):
        if not self.WebS is None and self.WebS.isRunning():
            self.WebS.stopServingRequests()

    def do_hello(self, args):
        """Says hello. If you provide a name, it will greet you with it."""
        if len(args) == 0:
            name = 'stranger'
        else:
            name = args
        print("Hello, %s", name)

    def do_quit(self, args):
        """Quits the program."""
        self.do_stopWeb(None)
        print("Quit.")
        raise SystemExit


if __name__ == '__main__':
    '''
    api = InstagramAPI(access_token='boh', client_id='boh', client_secret='boh')
    #popular_media = api.media_popular(count=20)
    associated_tags = api.tag_search("nofilter", count=20)
    #popular_media = api.tag_recent_media(count=20, max_tag_id, tag_name)'''

    prompt = MyPrompt()
    prompt.prompt = '> '
    prompt.cmdloop('Starting prompt...')

    
