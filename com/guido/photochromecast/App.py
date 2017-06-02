'''
Created on May 13, 2017

@author: guido
'''

from cmd import Cmd
from WebServer import WebServerClass
from Caster import CasterThread

class MyPrompt(Cmd):

    WebS = None
    Caster = None

    def do_web(self, args):
        """Starts web server, serving on port 8080. By default, 'demo-test' is used as a folder"""
        if len(args) == 0:
            print("Using demo-test folder")
            folder = 'demo-test'
        else:
            l = args.split()
            if len(l) > 1:
                print("Too many arguments dude!")
                return
            else:
                folder = l[0]

        if self.WebS is None:
            self.WebS = WebServerClass(folder)
        
        if not self.WebS.isRunning():
            self.WebS.startServingRequests()
    
    def do_stopWeb(self, args):
        """Stops web server."""
        if not self.WebS is None and self.WebS.isRunning():
            self.WebS.stopServingRequests()
    
    def do_connect(self, args):
        """Connects to a Chromecast with the given [name]."""
        l = args.split()
        if len(l) != 1:
            print("I need a name to connect to...")
            return
        else:
            if self.WebS is None:
                print "First of all you need to start the web server!"
            else:
                msg = self.Caster.connectTo(l[0])
                self.Caster.bindWebServer(self.WebS)
                print(msg)
    
    def do_cast(self, args):
        """Starts casting to a connected Chromecast."""
        if not self.Caster.isStarted() and self.Caster.isConnected():
            self.Caster.start()
        elif self.Caster.isStarted():
            print("Casting is already running!")
        else:
            print("Please connect to a Chromecast first!")
        
    def do_stop(self, args):
        """Stops casting to a connected Chromecast."""
        if self.Caster.isStarted():
            self.Caster.stop()
        else:
            print("Casting is not started yet! Please start it first.")
    
    def do_time(self, args):
        """Change current slideshow time in use."""
        l = args.split()
        if len(l) != 1:
            print("Pass a new slideshow timeout")
            return

        if self.Caster.isStarted():
            self.Caster.changeSlideShowTimeout(l[0])
        else:
            print("Start Casting first!")

    def do_skip(self, args):
        """Skip current displaying media."""
        if self.Caster.isStarted():
            self.Caster.skipCurrentMedia()
        else:
            print("Start Casting first!")

    def do_find(self, args):
        """Finds Chromecasts in range."""
        self.Caster.findChromecasts()
        print(self.Caster.printChromecasts())

    def do_quit(self, args):
        """Quits the program."""
        self.do_stopWeb(None)
        if self.Caster.isConnected():
            self.Caster.stop()

        print("Quit.")
        raise SystemExit

    def emptyline(self):
        return


if __name__ == '__main__':
    prompt = MyPrompt()
    prompt.prompt = '> '
    
    prompt.Caster = CasterThread(10)
    prompt.Caster.findChromecasts()
    casts = prompt.Caster.printChromecasts()
    prompt.cmdloop('Welcome! Type "help" for further info\n'
                   + '1. If found, available Chromecasts will be reported immediately\n'
                   + '2. Find Chromecasts with the command "find"\n'
                   + '3. Start web engine with "web"\n'
                   + '4. Connect with "connect" and then "cast"\n\n'
                   + casts)
