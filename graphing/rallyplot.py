#!/usr/bin/env python
from datetime import datetime
from collections import OrderedDict
import csv
import os
import re
import subprocess
import sys
import matplotlib
import matplotlib.pyplot as plt

services = ['keystone', 'nova', 'neutron']

# Saved Measurements:
measurements = ['min', 'median', '90%ile', '95%ile', 'Max', 'Avg', 'Success%', 'Count']

# Structure of compiled results dictionary:
# results[service][test][iteration][#workers][concurrency][measurement] = value

def main():
    compiled_results = OrderedDict()
    # Should be /home/<user>/browbeat/graphing:
    rallyplot_path = os.path.dirname(os.path.realpath(__file__))
    browbeat_path = rallyplot_path.replace('/graphing', '')

    for service in services:
        if service not in compiled_results:
            compiled_results[service] = OrderedDict()

        # Tests we compile results on is based on browbeat/(service)/(test file)
        tests = os.listdir('{}/{}'.format(browbeat_path, service))
        if 'README.md' in tests:
            tests.remove('README.md')

        for test in tests:
            if test not in compiled_results[service]:
                compiled_results[service][test] = OrderedDict()

            # Obtain results files based on regular expression with each test from above
            results = [f for f in os.listdir('{}/results'.format(browbeat_path)) if re.match(r'[a-zA-Z0-9\-]*-{}-[0-9]*-iteration_[0-9]*-{}-[0-9]*\.log'.format(service, test), f)]
            for result_file in results:

                # Extract worker count, iteration and concurrency of test
                extract_numbers = re.search('[a-zA-Z0-9\-]*-{}-([0-9]*)-iteration_([0-9]*)-{}-([0-9]*)\.log'.format(service, test), result_file)
                if extract_numbers:
                    w_count = int(extract_numbers.group(1))
                    iteration = int(extract_numbers.group(2))
                    concurrency = extract_numbers.group(3)

                print 'Service: {}, Test: {}, Worker Count: {}, Concurrency: {}, Iteration: {}'.format(service, test, w_count, concurrency, iteration)
                if iteration not in compiled_results[service][test]:
                    compiled_results[service][test][iteration] = OrderedDict()
                if w_count not in compiled_results[service][test][iteration]:
                    compiled_results[service][test][iteration][w_count] = OrderedDict()
                if concurrency not in compiled_results[service][test][iteration][w_count]:
                    compiled_results[service][test][iteration][w_count][concurrency] = OrderedDict()

                grep_cmd = subprocess.Popen(['grep', 'total', '{}/results/{}'.format(browbeat_path, result_file)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err =  grep_cmd.communicate()
                output = [s.strip() for s in out.strip().split('|') if s]
                compiled_results[service][test][iteration][w_count][concurrency]['min'] = output[1]
                compiled_results[service][test][iteration][w_count][concurrency]['median'] = output[2]
                compiled_results[service][test][iteration][w_count][concurrency]['90%ile'] = output[3]
                compiled_results[service][test][iteration][w_count][concurrency]['95%ile'] = output[4]
                compiled_results[service][test][iteration][w_count][concurrency]['Max'] = output[5]
                compiled_results[service][test][iteration][w_count][concurrency]['Avg'] = output[6]
                compiled_results[service][test][iteration][w_count][concurrency]['Success%'] = output[7].replace('%', '')
                compiled_results[service][test][iteration][w_count][concurrency]['Count'] = output[8]

    rally_graph_dir = '{}/rally-compiled-graphs'.format(browbeat_path)
    if not os.path.exists(rally_graph_dir):
        os.mkdir(rally_graph_dir)

    # Now graph results based on measurements list:
    for service in compiled_results:
        for test in compiled_results[service]:
            # Assumption is all tests have same number of iterations!!!
            for iteration in compiled_results[service][test]:
                for measurement in measurements:
                    concurrency_dict = OrderedDict()
                    for worker_count in compiled_results[service][test][iteration]:
                        for concurrency in compiled_results[service][test][iteration][worker_count]:
                            if concurrency not in concurrency_dict:
                                concurrency_dict[concurrency] = []
                            concurrency_dict[concurrency].append(compiled_results[service][test][iteration][worker_count][concurrency][measurement])

                    graph_file_name = '{}/{}-{}-{}-{}.png'.format(rally_graph_dir, service, test, iteration, measurement)
                    print '----------------------------------------------------------'
                    print 'Service: {}'.format(service)
                    print 'Test: {}'.format(test)
                    print 'Iteration: {}'.format(iteration)
                    print 'Measurement: {}'.format(measurement)
                    print 'File Name: {}'.format(graph_file_name)
                    print 'X-Axis (Worker Counts): {}'.format(compiled_results[service][test][iteration].keys())
                    print 'X-Axis (# of values per series): {}'.format(len(compiled_results[service][test][iteration].keys()))
                    print '# of Series (# of Concurrencies tested): {}'.format(len(compiled_results[service][test][iteration][worker_count].keys()))
                    for series in concurrency_dict:
                        print 'Series: {}, Values: {}'.format(series, concurrency_dict[series])
                    print 'Legend: {}'.format(concurrency_dict.keys())
                    print '----------------------------------------------------------'
                    plt.title('Service: {}, Test: {}, Iteration: {}'.format(service, test, iteration))
                    plt.xlabel('Workers')
                    plt.ylabel('{} Time (s)'.format(measurement))
                    for series in concurrency_dict:
                        plt.plot(compiled_results[service][test][iteration].keys(), concurrency_dict[series])
                    plt.legend(concurrency_dict.keys())  # Constant Concurrencies
                    plt.savefig(graph_file_name, bbox_inches='tight')
                    plt.close()


if __name__ == "__main__":
    sys.exit(main())
