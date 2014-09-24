#!/usr/bin/env python
import sys
import ConfigParser
import inspect

sys.path.append('test_code')

from os import path
from time import time

from parameters_parser import parameters
from network_builder import *
from test_code import *



class conf(parameters):
    def checkCorrectness(self):
        self.checkNeededParams()
        return True

class configurationFile():

    mandatoryOptions = {"testModule":None
            , "testClass":None}
    confParams = {}
    className = None
    def __init__(self, fileName, stanza):
        # check if filename esists
        try:
            fd =  open(fileName, "r")
        except IOError:
            error("Can not open the configuration file: " + fileName\
                + "\n")
            sys.exit(1)
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read(fileName)

        self.testName = stanza 
        if stanza not in self.parser.sections():
            error("Can not find configuration " + stanza \
                    + " in file " + fileName + "\n")
            sys.exit(1)
        for o in self.mandatoryOptions:
            self.mandatoryOptions[o] = \
                self.getConfigurations(o, raiseError=True)

        moduleName = "test_code." + self.mandatoryOptions['testModule']
        if moduleName not in sys.modules:
            errorString = "ERROR: no " \
                + self.mandatoryOptions['testModule'] \
                + " module  has been loaded!\n"
            error(errorString)
            sys.exit(1)

        if self.mandatoryOptions['testClass'] not in \
                zip(*inspect.getmembers(sys.modules[moduleName]))[0]:
            errorString = "ERROR: no " \
                + self.mandatoryOptions['testClass'] \
                + " simulation class is present in "\
                + moduleName + "\n"
            error(errorString)
            sys.exit(1)

        self.className = getattr(sys.modules[moduleName],
            self.mandatoryOptions['testClass'])

        for name, value in self.parser.items(self.testName):
            self.confParams[name] = value

    def getConfigurations(self, name, raiseError=False):
        try:
            r = self.parser.get(self.testName, name)
        except ConfigParser.NoOptionError:
            if raiseError:
                error("No option \'" + name + "\' found!\n")
                sys.exit()
            else:
                return None
        return r

if __name__ == '__main__':
    setLogLevel('info')
    need = [
            ("-f", ["configFile", True, "",
                "file with the available configurations", str]),
            ("-t", ["testName", True, "",
                "base name for test output", str])
           ]
    opt = [
            ("-d", ["drawGraph", False, False,
                "draw the graph before you run the test", int]),
            ("-g", ["graphFile", True, "",
                "file with the topology (overrides configuration)", str])
          ]

    P = conf(path.basename(__file__),need, opt)
    P.parseArgs()
    if P.checkCorrectness() == False:
        P.printUsage()
        sys.exit(1)

    configFile = P.getParam("configFile")
    testName = P.getParam("testName")
    C = configurationFile(configFile, testName)
    #import code
    #code.interact(local=locals())
    # parse the conf file
    networkGraph = P.getParam("graphFile")
    if networkGraph == "":
        networkGraph = C.getConfigurations("graphDefinition")
        if networkGraph == None:
            error("No graph topology specified in config file or command " + \
                "line!\n")
            sys.exit(1)
    drawGraph = P.getParam("drawGraph")

    net = GraphNet(networkGraph, draw = drawGraph)
    net.start()
    net.enableForwarding()
    net.setShortestRoutes()
#    CLI(net)
    testPath = testName+"_"+str(int(time()))
    for i in range(1):
        c = "peerstreamer.PSHostsTest"
        info("+++++++ Round: "+str(i+1) + '\n')
        #test = PSRandomTest(net,duration=6,name=test_name,num_peers=2)
        test = C.className(net, testPath, C.confParams)
        test.runTest()
    net.stop()
    test.changePermissions()
    info("*** Done with experiment: "+test_name+"\n")
