def dict_remove(the_dict, item):
    """Remove an item from a dictionary."""
    del the_dict[item]
    return the_dict


def hosts_to_dictionary(arg):
    """Changes list format of hosts to dictionary format.  The key of the dictionary is the index
    of the host. The index is defined by the host's suffix, example: overcloud-controller-10 is 10.
    If there is no suffix, I use an incremented value above 1000000."""

    dictionary = {}
    nonindex = 1000000
    for item in arg:
        if '-' in item:
            idx = item.rindex('-')
            dictionary[int(item[idx + 1:])] = item
        else:
            nonindex += 1
            dictionary[nonindex] = item
    return dictionary


def ini_value(key_value):
    """Strips key= from key=value from ini configuration data"""
    equals_idx = key_value.index('=') + 1
    return key_value[equals_idx:]


def to_grafana_refid(number):
    """Convert a number to a string starting at character a and incrementing.  This only accounts
    for a to zz, anything greater than zz is probably too much to graph anyway."""
    character1 = ''
    idx = -1
    while number > 25:
        idx = idx + 1
        number -= 26
    else:
        if idx != -1:
            character1 = chr(idx + 65)
    return character1 + chr(number + 65)


class FilterModule(object):
    def filters(self):
      return {
        'dict_remove': dict_remove,
        'ini_value': ini_value,
        'hosts_to_dictionary': hosts_to_dictionary,
        'to_grafana_refid': to_grafana_refid,
        }
