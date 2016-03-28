#!/usr/bin/env python
import json
import math
import matplotlib.pyplot as plt
import argparse
import os
import sys

def getiter(prog_dict):
    density = prog_dict['deployment']['accommodation'][2]['density']
    compute = prog_dict['deployment']['accommodation'][3]['compute_nodes']
    iterval = density*compute
    if(prog_dict['deployment']['accommodation'][0]=="pair" and
                 prog_dict['deployment']['accommodation'][1]=="single_room"):
        iterval //=2
    iterlist = []
    if prog_dict['execution']['progression'] in ['arithmetic', 'linear',
                                                 'linear_progression']:
        iterlist = range(1,iterval+1)
    elif prog_dict['execution']['progression'] in ['geometric', 'quadratic',
                                                   'quadratic_progression']:
        iterlist = [iterval]
        while iterval > 1:
            iterval //= 2
            iterlist.append(iterval)
            iterlist.reverse()
    elif prog_dict['execution']['progression'] == None:
        iterlist.append(iterval)
    return iterlist


def get_uuidlist(data):
    uuidlist = []
    for key in data['records'].iterkeys():
        uuidlist.append(key)
    return uuidlist

def get_agentlist(uuidlist, data):
    agentset=set()
    for uuid in uuidlist:
        agentname = data['records'][uuid]['agent']
        agentset.add(agentname)
    agentlist = list(agentset)
    agentlist.sort()
    return agentlist


def generate_aggregated_graphs(data, fname):
    for key in data['scenarios'].iterkeys():
        time1 = data['scenarios'][key]['execution']['tests'][0]['time']
        time = range(time1-1)
        density = (data['scenarios'][key]['deployment']
                       ['accommodation'][2]['density'])
        concur_list=getiter(data['scenarios'][key])
        uuidlist = get_uuidlist(data)
        title_name = (data['scenarios'][key]['title']).split('/')
        for concur in concur_list:
            countlist=[0]*(time1-1)
            for uuid in uuidlist:
                if data['records'][uuid]['concurrency'] == concur:
                    if data['records'][uuid]['status'] == "ok":
                        for index in range(time1-1):
                            countlist[index] += ((data['records'][uuid]
                                         ['samples'][index][1])/math.pow(10,6))
            plt.xlabel('Time in seconds')
            plt.ylabel('Throughput in Mbps')
            plt.title('Aggregated Throuhput for concurrencies \non node\n{}'.format(
                      data['records'][uuid]['node']),loc='left')
            plt.title(title_name[10],loc='right')
            plt.plot(time,countlist, linewidth=1,marker='o',
                     label="Concurrency:{}".format(concur))
            plt.grid()
        plt.legend(loc=9, prop={'size':8}, bbox_to_anchor=(0.5, -0.1),
                   ncol=concur)
        plt.savefig(os.path.splitext(fname)[0]+'.png', bbox_inches='tight')
        print("Generated plot for aggregated throughput for scenario {}".
              format(title_name[10]))
        plt.close()


def generate_perinstance_graphs(data, fname):
    uuidlist = get_uuidlist(data)
    agentlist = get_agentlist(uuidlist, data)
    for key in data['scenarios'].iterkeys():
        time1 = data['scenarios'][key]['execution']['tests'][0]['time']
        time = range(time1-1)
        density=(data['scenarios'][key]['deployment']
                     ['accommodation'][2]['density'])
        concur_list=getiter(data['scenarios'][key])
        title_name = (data['scenarios'][key]['title']).split('/')
        for agent in agentlist:
            resultlist=[0]*(time1-1)
            for concur in concur_list:
                for uuid in uuidlist:
                    if (data['records'][uuid]['concurrency'] == concur and
                        data['records'][uuid]['agent'] == agent):
                        for index in range(time1-1):
                            if data['records'][uuid]['status'] == "ok":
                                resultlist[index] = ((data['records'][uuid]
                                        ['samples'][index][1])/math.pow(10,6))
                        plt.xlabel('Time in seconds')
                        plt.ylabel('Throughput in Mbps')
                        plt.title('Throughput for {} \non node \n{}'.format(
                                  agent, data['records'][uuid]['node']), loc='left')
                        plt.title(title_name[10],loc='right')
                        plt.plot(time,resultlist, linewidth=1,marker='o',
                                 label="Concurrency:{}".format(concur))
                        plt.grid()
            plt.legend(loc=9, prop={'size':8}, bbox_to_anchor=(0.5, -0.1),
                       ncol=concur )
            plt.savefig(os.path.splitext(fname)[0]+ '_' + agent + '.png', bbox_inches='tight')
            print("Generated plot for agent {} in scenario {}".format(
                  agent, title_name[10]))
            plt.close()
def main():
    filelist=[]
    parser = argparse.ArgumentParser(
             description='Processes shaker results into aggregated graphs')
    parser.add_argument('result_dir',
                       help='Name of the directory in which results are stored'
                            ' Example: 20160226-101636')
    args = parser.parse_args()
    shakerplot_path = os.path.dirname(os.path.realpath(__file__))
    results_path = os.path.join(shakerplot_path.replace('graphing',
                                'results'), args.result_dir)
    if not os.path.isdir(results_path):
        print "ERROR Directory doesn't exist"
        exit(1)
    for root, dirs, files in os.walk(results_path, topdown=False):
        for name in files:
            if name.endswith('.json'):
                filelist.append(os.path.join(root, name))
    for fname in filelist:
        with open(fname) as data_file:
            data = json.load(data_file)
        generate_aggregated_graphs(data, fname)
        generate_perinstance_graphs(data, fname)

if __name__ == "__main__":
    sys.exit(main())
