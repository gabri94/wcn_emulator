
import sys
from network_builder import *
from os import kill, path, makedirs
from matplotlib.pyplot import ion
from random import sample, randint
import time
from test_generic import *
sys.path.append('../')


class princeTest(MininetTest):

    def __init__(self, mininet, duration=10):
        super(princeTest, self).__init__(mininet, path, duration)
        self.mininet = mininet
        self.centList = []
        self.stopNodes = []
        self.stopNodeList = []
        self.graph = mininet.gg
        self.olsr_conf_template = """
        DebugLevel  1
        IpVersion 4
        FIBMetric "flat"
        LinkQualityFishEye  0
        LockFile "%s"
        Hna4{}
        Hna6{}

        LoadPlugin "../olsrd/lib/netjson/olsrd_netjson.so.1.1"{
            PlParam "accept" "0.0.0.0"
            PlParam "port" "2010"
        }

        LoadPlugin "../olsrd/lib/poprouting/olsrd_poprouting.so.0.1"{
            PlParam "accept" "0.0.0.0"
            PlParam "port" "1234"
        }

        InterfaceDefaults {}

        Interface %s {}
        """

        self.prince_conf_template = """
        {
            "proto": {
                "protocol": "olsr",
                "host": "%s",
                "port": 2010,
                "timer_port": 1234,
                "refresh": 5
            },
            "graph-parser": {
                "heuristic": 1,
                "weights": 1,
                "recursive": 0,
                "stop_unchanged": 0,
                "multithreaded": 0
            }
        }
        """
        self.stopNodeList = self.getCentrality()

    def launch_sniffer(self, host):

        cmd = "tcpdump -i any -n -X -e "

        logfile = self.prefix + host.name + "-dump.log"

        params = {}
        params['>'] = logfile
        params['2>'] = logfile

        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def launchOLSR(self, host, args):
        cmd = "../olsrd/olsrd " + args

        log_str = "Host " + host.name + " launching command:\n"
        info(log_str)
        info(cmd + "\n")
        logfile = self.prefix + host.name + "_olsr.log"

        params = {}
        params['>'] = logfile
        params['2>'] = logfile

        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def launchPrince(self, host, args):
        cmd = "../poprouting/output/prince " + args

        log_str = "Host " + host.name + " launching command:\n"
        info(log_str)
        info(cmd + "\n")
        logfile = self.prefix + host.name + "_prince.log"

        params = {}
        params['>'] = logfile
        params['2>'] = logfile

        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def launchPing(self, host):
        idps = randint(0, 100)
        logfile = self.prefix + host.name.split('_')[0] + \
            "-" + str(idps) + "_ping_$(date +%s).log"

        cmd = "ping " + self.destination
        params = {}
        params['>'] = logfile
        params['2>'] = logfile

        return self.bgCmd(host, True, cmd,
                          *reduce(lambda x, y: x + y, params.items()))

    def runTest(self):
        info("*** Launching Prince test\n")
        info("Data folder: " + self.prefix + "\n")
        self.setupNetwork(poprouting=True)
        self.performTests()
        info("Waiting completion...\n")
        self.wait(float(self.duration), log_resources={'net': 'netusage.csv'})
        self.tearDownNetwork()

    def setupNetwork(self, poprouting, dump=False):
        for idx, h in enumerate(self.getAllHosts()):
            intf = h.intfList()
            intf_list = ' '.join(["\"" + i.name + "\"" for i in intf])
            olsr_conf_file = self.prefix + h.name + "_olsr.conf"
            olsr_lock_file = "/var/run/" + h.name + str(time.time()) + ".lock"
            f_olsr = open(olsr_conf_file, "w")
            print >> f_olsr, self.olsr_conf_template % (olsr_lock_file, intf_list)
            f_olsr.close()
            args_olsr = "-f " + os.path.abspath(olsr_conf_file)

            prince_conf_file = self.prefix + h.name + "_prince.json"
            f_prince = open(prince_conf_file, "w")
            print >> f_prince, self.prince_conf_template % (h.defaultIntf().ip)
            f_prince.close()
            args_prince = os.path.abspath(prince_conf_file)

            launch_pid = self.launchOLSR(h, args_olsr)
            if poprouting:
                launch_pid = self.launchPrince(h, args_prince)
            if dump:
                self.launch_sniffer(h)

    def tearDownNetwork(self):
        self.killAll()

    def performTests(self):
        for idx, h in enumerate(self.getAllHosts()):
            if h.defaultIntf().ip != self.destination:
                self.launchPing(h)
        self.wait(float(self.killwait))
        self.nodeCrashed = self.stopNodeList.pop(0)
        if self.nodeCrashed:
            print "Killing " + str(self.nodeCrashed) + "\n"
            self.sendSignal(signal.SIGKILL, self.nodeCrashed)

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

    def getCentrality(self):
        node_centrality_posteriori = {}
        centrality = {}
        for n in self.graph.nodes():
            gg = self.graph.copy()
            edges = self.graph.edges([n])
            gg.remove_node(n)
            # compute the connected components
            # WARNING: connected_components should return a list
            # sorted by size, largest first. It does not, so i resort them
            unsorted_comp = list(nx.connected_components(gg))
            comp = sorted(unsorted_comp, key=lambda x: -len(x))
            # re-add the node
            gg.add_node(n)
            # re-add the edges to nodes in the main component
            for (fr, to) in edges:
                if fr in comp[0]:
                    gg.add_edge(fr, n)
                if to in comp[0]:
                    gg.add_edge(n, to)
            # now compute the centrality. This tells how important is the node
            # for the main connected component. If this is 0, it is not worth
            # to remove this node
            cent = nx.betweenness_centrality(gg)[n]
            isolated_nodes = [x for component in comp[1:] for x in component]
            node_centrality_posteriori[n] = [cent, [n] + isolated_nodes]
            centrality[n] = cent
        betw = [x for x in nx.betweenness_centrality(self.graph).items()
                if x[1] > 0 and node_centrality_posteriori[x[0]][0] > 0]

        return [node_centrality_posteriori[k[0]][1] for k in sorted(betw, key=lambda x: -x[1])]


class princeRandomTest(princeTest):

    def __init__(self, mininet, name, args):

        duration = int(args["duration"])
        self.killwait = int(args["kill_wait"])
        super(princeRandomTest, self).__init__(mininet, duration)
        self.kill = self.getHostSample(1)[0].defaultIntf().ip
        self.destination = self.getHostSample(1)[0].defaultIntf().ip
        self.setPrefix(name)