import sys
import os
import numpy as np
import csv
import pandas
import networkx as nx
from scipy import stats
import math

graph=None

def mean_val(subpath):
    global graph
    breaks = []
    dirs = os.listdir(subpath)
    dirs.sort(key=lambda x: int(x.split('_')[1]))
    for node in dirs:
        if not graph:
            graph = nx.read_adjlist("%s/%s/topology.adj"%(subpath, node))
        with open("%s/%s/breakage.dat" % (subpath, node)) as f:
            data = []
            reader = csv.reader(f)
            for row in reader:
                d = {}
                d['timestamp'] = int(row[0])
                d['correct'] = int(row[1])
                data.append(d)
            m_route = max(data, key=lambda x: x['correct'])['correct'] #Search for the max number of route (right one)
            unconverged_index = 0
            for i in range (len(data)):
                if data[i]['correct'] < m_route:
                    if data[unconverged_index]['correct'] <= data[i]['correct']:
                        unconverged_index += 1 
                    else:
                        print("Error2")
                        exit(0)
                else:
                    break
            if unconverged_index > len(data)/2:
                print("Error")
                exit(0)

            if unconverged_index> 5:
                print("%s/%s"%(subpath, node))
            filtered = data[unconverged_index:-5] #Remove all the data before the wait time and the last 10 seconds
            stable = sorted([(d['timestamp'], d['correct']) for d in filtered if d['correct'] != m_route], key=lambda x: x[0])  # filter all about the fluctuations
            breakage = 0
            try:
                longest_seq = max(np.split(stable, np.where(np.diff(stable[0]) != 1)[0]+1), key=len).tolist()
                for l in longest_seq:
                    breakage += 0.1*(m_route-l[1])
            except IndexError:
                pass
            breaks.append(breakage)
    return (breaks)


def pick_first_folder(path):
    runs = os.listdir(path)
    runs.sort()
    nodes = os.listdir(path+runs[0]+"/POP/")
    nodes.sort(key=lambda x: int(x.split('_')[1]))
    return (nodes, runs)
    
    

def main(path):

    nodes,runs = pick_first_folder(path)
    global graph
    samples = len(nodes)
    try:
        n_run = int(sys.argv[2])
    except:
        n_run = len(runs)
    data = np.empty([n_run, 3, samples])
    dirs = os.listdir(path)
    dirs.sort()
    i=0
    for d in dirs[:n_run]:
        j=0
        params = ["NOPOP", "POP", "POPPEN"]
        for p in params: 
            breaks =  mean_val("%s/%s/%s" % (path, d, p))
            data[i,j] = breaks
            j+=1 
        i+=1

    for i in range(n_run):
        print pandas.DataFrame(data[i], columns=nodes)
    #print pandas.DataFrame(d)
    results = np.zeros([3,3,samples])
    means = np.mean(data, (0))
    stds = np.std(data, (0))
    results[0] = means
    results[1:] = stats.t.interval(0.95, samples-1, loc=means, scale=stds/math.sqrt(samples))
    results=np.reshape(results, (9,samples)).T.tolist()
    bet = nx.betweenness_centrality(graph)
    for i in range(samples):
        results[i].append(nodes[i])
        results[i].append(bet[results[i][9]])
    results.sort(key=lambda x:x[10]) 
    for i in range(samples):
        print("%f,%f,%f,%f,%f,%f,%f,%f,%f,%s,%f"% tuple(results[i]))
    #print pandas.DataFrame(results,columns=labels)
    #np.save('temp.dat', results)
    #print pandas.DataFrame(np.std(data,(0)))
    means = np.average(data, 0)
    print(means)
    mean = np.average(means, (1), weights=[10./20, 10./20, 1./41])
    print("%f,%f,%f"%tuple(mean))

if __name__ == '__main__':
    main(sys.argv[1])
