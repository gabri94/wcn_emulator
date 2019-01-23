import sys
import os
import numpy as np
import csv
import pandas

def mean_val(subpath):
    breaks = []
    dirs = os.listdir(subpath)
    for node in dirs:
        with open("%s/%s/breakage.dat" % (subpath, node)) as f:
            data = []
            reader = csv.reader(f)
            for row in reader:
                d = {}
                d['timestamp'] = int(row[0])
                d['correct'] = int(row[1])
                data.append(d)
            m_route = max(data, key=lambda x: x['correct'])['correct'] #Search for the max number of route (right one)
            filtered = data[5:-5] #Remove all the data before the wait time and the last 10 seconds
            stable = sorted([d['timestamp'] for d in filtered if d['correct'] != m_route])  # filter all about the fluctuations
            longest_seq = max(np.split(stable, np.where(np.diff(stable) != 5)[0]+1), key=len).tolist()
            breakage = float(len(longest_seq))*0.5
            breaks.append(breakage)
            #print "%.2fs,%s"%(breakage, node) #ds
    return breaks

def main(path, n_run):
    samples = 8
    n_params = 2
    data = np.empty([n_run, n_params, samples])
    dirs = os.listdir(path)
    dirs.sort()
    i=0
    for d in dirs[:n_run]:
        j=0
        params = ["POP", "POPPEN"]
        for p in params[:n_params]: 
            breaks =  mean_val("%s/%s/%s" % (path, d, p))
            data[i,j]=breaks
            j+=1
        i+=1

    for i in range(n_run):
        print pandas.DataFrame(data[i])
    print np.mean(data, (2,0))

if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]))