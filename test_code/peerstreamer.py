
import sys
sys.path.append('../')
from network_builder import *
from os import kill, path, makedirs
from matplotlib.pyplot import ion
from random import sample, randint

from test_generic import *

class PSTest(MininetTest):
    def __init__(self,mininet,duration=300):
        super(PSTest,self).__init__(mininet)
        self.source = None
        self.hosts = []
        self.duration = duration
        self.prefix = ''

    def setPrefix(self,name):
        self.prefix = str(name)+'_'+str(self.duration)+'_'+str(len(self.hosts)+1)+'hosts/' 
        if not path.exists(self.prefix):
                makedirs(self.prefix)

    def launchPS(self,host,params,stdout,stderr):
        cmd = "./streamer"
        params['-c'] = '38'
#        params['-M'] = '5'
#        params['-O'] = '3'
        params['--chunk_log'] = ''
        params['>'] = stdout
        params['2>'] = stderr
        return self.bgCmd(host,True,cmd,*reduce(lambda x, y: x + y, params.items()))

    def launchPeer(self,host,source,source_port=7000):
        idps = randint(0,100)
        logfile = self.prefix+host.name.split('_')[0]+"-"+str(idps)+"_peerstreamer_normal_$(date +%s).log"
        params = {}
        params['-i'] = source.defaultIntf().ip
        params['-p'] = str(source_port)
        params['-P'] = str(randint(4000,8000))
        return self.launchPS(host,params,'/dev/null',logfile)

    def launchSource(self,host,chunk_mult=1,source_port=7000):
        idps = randint(0,100)
        video_file = "bunny.ts,loop=1"
        logfile = self.prefix+host.name.split('_')[0]+"-"+str(idps)+"_source_normal_$(date +%s).log"
        params = {}
        params['-I'] = host.defaultIntf().name
        params['-P'] = str(source_port)
        params['-f'] = video_file
        params['-m'] = str(chunk_mult)
        return self.launchPS(host,params,'/dev/null',logfile)

    def runTest(self):
        info("*** Launching PeerStreamer test\n")
        info("Data folder: "+self.prefix+"\n")
        if self.source:
            self.launchSource(self.source)

        for h in self.hosts:
            self.launchPeer(h,self.source)
        info("Waiting completion...\n")
        sleep(self.duration)

        self.killAll()

class PSHostsTest(PSTest):
    def __init__(self,mininet,source_name,peer_names,duration=300,name=None):
        super(PSHostsTest,self).__init__(mininet,duration=duration)
        self.source = mininet.get(source_name)
        for n in peer_names:
            self.hosts.append(mininet.get(n))
        self.setPrefix(name)

class PSRandomTest(PSTest):
    def __init__(self,mininet,duration=300,num_peers=5,name=None):
        super(PSRandomTest,self).__init__(mininet,duration)
        self.hosts = self.getHostSample(num_peers)
        if len(self.hosts) > 0:
            self.source = self.hosts.pop()
        self.setPrefix(name)


