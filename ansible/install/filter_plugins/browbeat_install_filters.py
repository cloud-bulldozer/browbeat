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


class FilterModule(object):
    def filters(self):
      return {
        'dict_remove': dict_remove,
        'hosts_to_dictionary': hosts_to_dictionary,
        }
