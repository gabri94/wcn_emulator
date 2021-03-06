import sys
from network_builder import *
from os import kill, path, makedirs
from matplotlib.pyplot import ion
from random import sample, randint
from mininet.util import pmonitor
from measure_breakage_time import resultParser
import time
import graph_utils as gu
import networkx as nx
import numpy as np
from test_generic import *
sys.path.append('../')


class princeHeuristicKill(MininetTest):
    def __init__(self, mininet, name, kill, args):
        self.duration = int(args["duration"])
        super(princeHeuristicKill, self).__init__(mininet, path, self.duration)
        self.mininet = mininet
        self.centList = []
        self.stopNodes = []
        self.stopNodeList = []
        self.graph = mininet.gg
        self.prince_conf_template = """
{
    "proto": {
        "protocol": "olsr",
        "host": "%s",
        "port": 2009,
        "timer_port": 1234,
        "refresh": 5
    },
    "graph-parser": {
        "heuristic": 1,
        "weights": 1,
        "recursive": 0,
        "stop_unchanged": 0,
        "multithreaded": 0,
        "cutpoint_penalization": %d
    }
}
"""
        self.poprouting = int(args["poprouting"])
        self.cutpoint_pen = int(args["cutpoint_pen"])
        self.setPrefix(name)
        self.olsr_conf_template = """
DebugLevel  1
IpVersion 4
FIBMetric "flat"
LinkQualityFishEye  0
LockFile "%s"
Hna4{}
Hna6{}

#This plugin is bugged
LoadPlugin "../olsrd/lib/netjson/olsrd_netjson.so.1.1"{
   PlParam "accept" "0.0.0.0"
   PlParam "port" "2010"
}

LoadPlugin "../olsrd/lib/txtinfo/olsrd_txtinfo.so.1.1"{
    PlParam "accept" "0.0.0.0"
    PlParam "port" "2008"
}

LoadPlugin "../olsrd/lib/jsoninfo/olsrd_jsoninfo.so.1.1"{
    PlParam "accept" "0.0.0.0"
    PlParam "port" "2009"
}

LoadPlugin "../olsrd/lib/poprouting/olsrd_poprouting.so.1.1"{
    PlParam "accept" "0.0.0.0"
    PlParam "port" "1234"
}

InterfaceDefaults {
    TcInterval 2.5
    TcValidityTime  7.5
    HelloInterval   1.0
    HelloValidityTime 3.0
}

%s"""
        self.heuristic = 1
        self.killwait = int(args["kill_wait"])
        self.weights = 1
        self.dump = 0
        self.kill_node = kill

    def launchPrince(self, host):
        prince_conf_file = self.prefix + host.name + "_prince.json"
        with open(prince_conf_file, "w") as f_prince:
            # logfile = os.path.abspath(self.prefix + host.name + "_prince.log")
            # with open(logfile, "w+") as fh:
            #     fh.close()
            # os.chmod(logfile, 0o777)
            print >> f_prince, self.prince_conf_template % (host.defaultIntf().ip, self.cutpoint_pen)
        args = os.path.abspath(prince_conf_file)
        logfile = self.prefix + host.name + "_prince_out.log"
        cmd = "exec ../prince/build/prince " + args
        # log_str = "Host " + host.name + " launching command:\n"
        # info(log_str)
        # info(cmd + "\n")
        params = {}
        params['>'] = logfile
        params['2>'] = logfile
        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def runTest(self):
        info("*** Launching Prince test\n")
        info("Data folder: " + self.prefix + "\n")
        plt.show()
        self.setupNetwork()
        info("\n")
        info("Waiting to kill the node...\n")
        self.performTests()
        info("Waiting completion...\n")
        self.wait(float(self.duration))
        # Stop all the route grabbing before the networks stops
        for pid in self.dump_pids:
            self.sendSig(pid, sig=signal.SIGTERM)
        # Stop the network
        self.tearDownNetwork()
        self.analyzeResults()
    
    def gen_olsr_if_block(self, host):
        intf = host.intfList()
        block = ""
        for i in intf:
            lqm = self.mininet.if_lqm[str(i)]
            block += "Interface \"%s\" {\nLinkQualityMult default %f\n}\n" % (i, lqm)
        return block

    def setupNetwork(self):
        self.dump_pids = []
        nx.write_adjlist(self.graph, self.prefix + "topology.adj")
        for idx, host in enumerate(self.getAllHosts()):
            intf = host.intfList()
            self.intf_list = ' '.join(["\"" + i.name + "\"" for i in intf])
            launch_pid = self.launchRouting(host)
            if self.poprouting:
                pid = self.launchPrince(host)
            if self.dump:
                self.launch_sniffer(host)
        for idx, host in enumerate(self.getAllHosts()):
            self.dump_pids.append(self.dumpRoute(host, self.killwait - 10))
            #self.dump_pids.append(self.dumpLink(host, self.killwait - 10))

    def dumpRoute(self, host, wait):
        logdir = self.prefix + "rtables/" + host.name
        logfile = self.prefix + host.name + "_dump_out.log"
        os.makedirs(logdir)
        cmd = "./dumpRoute.sh %s %d" % (logdir, wait)
        params = {}
        params['>'] = "/dev/null"  # logfile
        params['2>'] = "/dev/null"  # logfile
        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def dumpLink(self, host, wait):
        logdir = self.prefix + "links/" + host.name
        logfile = self.prefix + host.name + "_dump_out.log"
        os.makedirs(logdir)
        cmd = "./dumpLink.sh %s %d" % (logdir, wait)
        params = {}
        params['>'] = "/dev/null"  # logfile
        params['2>'] = "/dev/null"  # logfile
        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def launchRouting(self, host):
        olsr_conf_file = self.prefix + host.name + "_olsr.conf"
        olsr_lock_file = "/var/run/" + host.name + str(time.time()) + ".lock"
        with open(olsr_conf_file, "w") as f_olsr:
            ifblock = self.gen_olsr_if_block(host)
            print >> f_olsr, self.olsr_conf_template % (olsr_lock_file, ifblock)
        args = "-f " + os.path.abspath(olsr_conf_file)
        cmd = "../olsrd/olsrd " + args
        # log_str = "Host " + host.name + " launching command:\n"
        # info(log_str)
        # info(cmd + "\n")
        logfile = "/dev/null"  # self.prefix + host.name + "_olsr.log"

        params = {}
        params['>'] = logfile
        params['2>'] = logfile

        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def performTests(self):
        keep_time = 10
        self.wait(int(self.killwait - keep_time))
        # Signal the processes to start dumping keep_time before the killing of the node
        for pid in self.dump_pids:
            self.sendSig(pid=pid, sig=signal.SIGUSR2)
        self.wait(keep_time,  log_resources={'net': 'netusage.csv', 'cpu': 'cpuusage.csv'})
        print("Killing %s at time %d\n" % (self.kill_node, time.time()))
        self.sendSignal(signal.SIGUSR1, hostName=[self.kill_node])
        print("Killed at time %d\n" % (time.time()))

    def tearDownNetwork(self):
        self.killAll()

    def analyzeResults(self):
        p = resultParser()
        p.read_topologies_from_node(self.prefix + "/rtables/")
        p.reorder_logs()
        p.killed_node = self.kill_node
        p.cc_list = []
        graph = nx.read_adjlist(self.prefix + "/topology.adj")
        graph.remove_node(p.killed_node)
        for cc in nx.connected_components(graph):
            p.cc_list.append(map(lambda x: p.id_ip[x], cc))
        p.navigate_all_timestamps()
        print "time, correct_paths, loops, broken_paths, missing_dest"
        p.data_series.sort(key=lambda x: x[0])
        with open(self.prefix + "breakage.dat", "w") as breakage:
            for l in p.data_series:
                print >> breakage, ",".join(map(str, l))
        return

    def sendSignal(self, sig, hostName=""):
        for pid, h in self.pendingProc.items():
            if hostName:
                for host in hostName:
                    if host == h.name:
                        print "sending signal to host:", host, ", pid", pid
                        self.sendSig(pid, sig)
            # send to all
            else:
                print "sending signal to all hosts:", sig
                self.sendSig(pid, sig)
