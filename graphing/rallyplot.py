#!/usr/bin/env python
from datetime import datetime
from collections import OrderedDict
import argparse
import csv
import os
import re
import subprocess
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Saved Measurements:
measurements = ['Min', 'Median', '90%ile', '95%ile', 'Max', 'Avg', 'Success%', 'Count']

"""
Results directory structure:
".../browbeat/results/full-apache-fernet-keystone-36/keystone/keystone-cc/run-1/
 full-apache-fernet-keystone-36-iteration_1-keystone-cc-0256.log"
Structure of compiled results dictionary:
results[service][test][iteration][#workers][concurrency][measurement] = value
"""

def list_only_directories(the_directory):
    return [a_dir for a_dir in os.listdir(the_directory)
            if os.path.isdir(os.path.join(the_directory, a_dir)) ]


def main():
    parser = argparse.ArgumentParser(
        description='Processes multiple rally log files from brwowbeat into compiled graphs.')
    parser.add_argument('test_prefix', help='Use the resulting prefixed directories/files in '
        'browbeat results directory.')
    args = parser.parse_args()

    compiled_results = OrderedDict()
    compiled_issues = []
    # Should be /home/<user>/browbeat/graphing:
    rallyplot_path = os.path.dirname(os.path.realpath(__file__))
    browbeat_path = rallyplot_path.replace('/graphing', '')

    test_runs = [a_dir for a_dir in list_only_directories('{}/results/'.format(browbeat_path))
            if re.match('^{}-[A-Za-z]+-[0-9]+'.format(args.test_prefix), a_dir)]

    for test_run in test_runs:
        extract = re.search('{}-([a-zA-Z]*)-([0-9]*)'.format(args.test_prefix), test_run)
        skip = True
        if extract:
            service = extract.group(1)
            w_count = extract.group(2)
            skip = False
        else:
            print 'Potentially incorrect directory: {}'.format(test_run)
        if not skip:
            for service in os.listdir('{}/results/{}/'.format(browbeat_path, test_run)):
                if service not in compiled_results:
                    compiled_results[service] = OrderedDict()
                for test in os.listdir('{}/results/{}/{}/'.format(browbeat_path, test_run, service)):
                    if test not in compiled_results[service]:
                        compiled_results[service][test] = OrderedDict()
                    for iteration in os.listdir('{}/results/{}/{}/{}/'.format(browbeat_path, test_run, service, test)):
                        iter_num = int(iteration.replace('run-', ''))
                        if iter_num not in compiled_results[service][test]:
                            compiled_results[service][test][iter_num] = OrderedDict()
                        if w_count not in compiled_results[service][test][iter_num]:
                            compiled_results[service][test][iter_num][w_count] = OrderedDict()
                        result_files = os.listdir('{}/results/{}/{}/{}/{}/'.format(browbeat_path, test_run, service, test, iteration))
                        result_files = [a_file for a_file in result_files if re.match('.*log', a_file)]
                        for r_file in result_files:
                            # Extract concurrency of test
                            extract = re.search('{}-{}-{}-iteration_{}-{}-([0-9]*)\.log'.format(args.test_prefix, service, w_count, iter_num, test), r_file)
                            if extract:
                                concurrency = extract.group(1)
                            if concurrency not in compiled_results[service][test][iter_num][w_count]:
                                compiled_results[service][test][iter_num][w_count][concurrency] = OrderedDict()
                            result_file_full_path = '{}/results/{}/{}/{}/{}/{}'.format(browbeat_path, test_run, service, test, iteration, r_file)
                            # print 'Test_run: {}, Service: {}, Test: {}, iteration: {}, Concurrency: {}, Result_file: {}'.format(test_run, service, test, iteration, concurrency, r_file)
                            # print 'Full Path: {}'.format(result_file_full_path)

                            grep_cmd = subprocess.Popen(['grep', 'total', result_file_full_path],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            out, err =  grep_cmd.communicate()
                            if len(out) == 0:
                                print 'Could not find results. Setting to -1'
                                compiled_issues.append(r_file)
                                compiled_results[service][test][iter_num][w_count][concurrency]['Min'] = '-1'
                                compiled_results[service][test][iter_num][w_count][concurrency]['Median'] = '-1'
                                compiled_results[service][test][iter_num][w_count][concurrency]['90%ile'] = '-1'
                                compiled_results[service][test][iter_num][w_count][concurrency]['95%ile'] = '-1'
                                compiled_results[service][test][iter_num][w_count][concurrency]['Max'] = '-1'
                                compiled_results[service][test][iter_num][w_count][concurrency]['Avg'] = '-1'
                                compiled_results[service][test][iter_num][w_count][concurrency]['Success%'] = '0'
                                compiled_results[service][test][iter_num][w_count][concurrency]['Count'] = '-1'
                            else:
                                output = [s.strip() for s in out.strip().split('|') if s]
                                compiled_results[service][test][iter_num][w_count][concurrency]['Min'] = output[1]
                                compiled_results[service][test][iter_num][w_count][concurrency]['Median'] = output[2]
                                compiled_results[service][test][iter_num][w_count][concurrency]['90%ile'] = output[3]
                                compiled_results[service][test][iter_num][w_count][concurrency]['95%ile'] = output[4]
                                compiled_results[service][test][iter_num][w_count][concurrency]['Max'] = output[5]
                                compiled_results[service][test][iter_num][w_count][concurrency]['Avg'] = output[6]
                                compiled_results[service][test][iter_num][w_count][concurrency]['Success%'] = output[7].replace('%', '')
                                compiled_results[service][test][iter_num][w_count][concurrency]['Count'] = output[8]

    rally_graph_dir = '{}/results/{}-rally-compiled-graphs/'.format(browbeat_path, args.test_prefix)
    if not os.path.exists(rally_graph_dir):
        os.mkdir(rally_graph_dir)

    # Now graph results based on measurements list:
    for service in compiled_results:
        for test in compiled_results[service]:
            # Assumption is all tests have same number of iterations!!!
            for iteration in compiled_results[service][test]:
                for measurement in measurements:
                    concurrency_dict = {}
                    for worker_count in sorted(compiled_results[service][test][iteration].keys()):
                        for concurrency in compiled_results[service][test][iteration][worker_count]:
                            if concurrency not in concurrency_dict:
                                concurrency_dict[concurrency] = []
                            if str(compiled_results[service][test][iteration][worker_count][concurrency][measurement]) == "n/a":
                                # Rally will place n/a in place of an actual result when it fails
                                # completely, we can't graph n/a, so replace with -1
                                concurrency_dict[concurrency].append(-1)
                            else:
                                concurrency_dict[concurrency].append(float(compiled_results[service][test][iteration][worker_count][concurrency][measurement]))

                    graph_file_name = '{}{}-{}-{}-{}.png'.format(rally_graph_dir, service, test, iteration, measurement)
                    print '----------------------------------------------------------'
                    print 'Test Prefix: {}'.format(args.test_prefix)
                    print 'Service: {}'.format(service)
                    print 'Test: {}'.format(test)
                    print 'Iteration: {}'.format(iteration)
                    print 'Measurement: {}'.format(measurement)
                    print 'File Name: {}'.format(graph_file_name)
                    print 'X-Axis (Worker Counts): {}'.format(sorted(compiled_results[service][test][iteration].keys()))
                    print 'X-Axis (# of values per series): {}'.format(len(compiled_results[service][test][iteration].keys()))
                    print '# of Series (# of Concurrencies tested): {}'.format(len(compiled_results[service][test][iteration][worker_count].keys()))
                    for series in sorted(concurrency_dict):
                        print 'Series: {}, Values: {}'.format(series, concurrency_dict[series])
                    print 'Legend: {}'.format(sorted(concurrency_dict.keys()))
                    print '----------------------------------------------------------'
                    fig = plt.figure()
                    plt.title(
                        'Test Name: {}\n'
                        'Service: {}, Test: {}, Iteration: {}, Measurement: {}\n'
                        'Graphed from rally task log output'.format(args.test_prefix, service, test,
                            iteration, measurement))
                    plt.xlabel('Workers')
                    plt.ylabel('{} Time (s)'.format(measurement))
                    ax = fig.add_subplot(111)
                    for series in sorted(concurrency_dict.keys()):
                        plt_linewidth = 1
                        if '-1' in concurrency_dict[series]:
                            plt_linewidth = 2
                        plt.plot(sorted(compiled_results[service][test][iteration].keys()),
                            concurrency_dict[series], linewidth=plt_linewidth, label=series, marker='o')
                        for x, y in zip(sorted(compiled_results[service][test][iteration].keys()), 
                                concurrency_dict[series]):
                            ax.annotate('%s' % y, xy=(x,y), xytext=(4,4), textcoords='offset points')
                    plt.legend(loc='upper center', bbox_to_anchor=(1.12, 0.5), fancybox=True)
                    ax.grid(True)
                    plt.savefig(graph_file_name, bbox_inches='tight')
                    plt.close()

    # Print files that had an issue:
    print '----------------------------------------------------------'
    print 'Files missing results:'
    print '----------------------------------------------------------'
    for issue in compiled_issues:
        print 'File: {}'.format(issue)


if __name__ == "__main__":
    sys.exit(main())
