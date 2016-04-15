import logging
import os
import shutil
from subprocess import Popen, PIPE


class Tools:

    def __init__(self, config=None):
        self.logger = logging.getLogger('browbeat.Tools')
        self.config = config
        return None

    # Run command, return stdout as result
    def run_cmd(self, cmd):
        self.logger.debug("Running command : %s" % cmd)
        process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if len(stderr) > 0:
            return None
        else:
            return stdout.strip()

    # Find Command on host
    def find_cmd(self, cmd):
        _cmd = "which %s" % cmd
        self.logger.debug('Find Command : Command : %s' % _cmd)
        command = self.run_cmd(_cmd)
        if command is None:
            self.logger.error("Unable to find %s" % cmd)
            raise Exception("Unable to find command : '%s'" % cmd)
            return False
        else:
            return command.strip()

    def create_run_dir(self, results_dir, run):
        try:
            os.makedirs("%s/run-%s" % (results_dir, run))
            return "%s/run-%s" % (results_dir, run)
        except OSError as e:
            return False

    # Create directory for results
    def create_results_dir(self, results_dir, timestamp, service, scenario):
        try:
            os.makedirs("{}/{}/{}/{}".format(results_dir,
                                             timestamp, service, scenario))
            self.logger.debug("{}/{}/{}/{}".format(os.path.dirname(results_dir), timestamp, service,
                                                   scenario))
            return "{}/{}/{}/{}".format(os.path.dirname(results_dir), timestamp, service, scenario)
        except OSError as e:
            return False
