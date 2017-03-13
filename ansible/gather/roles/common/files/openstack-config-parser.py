import sys
# usage: openstack-config-parser.py [service] [config file] [output file]


def parse_config(serviceName, fileName):
    # a dict containing key/value
    # pairs, last value is what is
    # stored.
    values = {}
    with open(fileName) as config:
        section = None
        for line in config:
            pair = line.replace('#', '')
            pair = pair.replace('\n', '')
            pair = pair.replace('"', '')
            pair = pair.replace('\\', '')
            pair = pair.replace(' ', '')
            pair = pair.replace('<', '')
            pair = pair.replace('>', '')
            pair = pair.split('=')
            # excludes any line without a key/val pair
            valid_line = not line.startswith(
                "# ") and '[' not in line and line != '\n' and line != '#\n' and "password" not in line.lower()
            if line.startswith('['):
                section = line.replace('[','').replace(']','').replace('\n','')
            if '#' not in line and valid_line and not section == None:
                values["openstack_S_" + serviceName + "_S_" + section + "_S_" + pair[0]] = pair[1]
    return values


def try_type(val):
    try:
        int(val)
        return val
    except ValueError:
        try:
            float(val)
            return val
        except ValueError:
            if val.lower() in ("true", "false"):
                return val
            else:
                return "\"" + val + "\""


def print_vars_file(values, fileName):
    with open(fileName, 'w') as output:
        for key in values:
            output.write(key + ": " + try_type(values[key]) + "\n")


def main():
    output = parse_config(sys.argv[1], sys.argv[2])
    print_vars_file(output, sys.argv[3])

if __name__ == '__main__':
    sys.exit(main())
