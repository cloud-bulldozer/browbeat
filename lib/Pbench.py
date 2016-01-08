import logging
import sys
sys.path.append("./")
from Tools import *

class Pbench:

    def __init__(self,config,hosts):
        self.logger = logging.getLogger('browbeat.Pbench')
        self.tools = Tools()
        self.config = config
        self.hosts = hosts
        return None

    # PBench Start Tools
    def register_tools(self):
        tool="register-tool"
        register_tool=self.tools.find_cmd(tool)
        tool="clear-tools"
        clear_tools=self.tools.find_cmd(tool)
        interval = self.config['browbeat']['pbench']['interval']
        as_sudo = self.config['browbeat']['sudo']
        # Clear out old tools
        cmd = ""
        if as_sudo :
            cmd +="sudo "
        cmd = "%s" % clear_tools
        self.logger.info('PBench Clear : Command : %s' % cmd)
        self.tools.run_cmd(cmd)
        # Now Register tools
        self.logger.info('PBench register tools')
        for tool in self.config['browbeat']['pbench']['tools'] :
            cmd = ""
            if as_sudo :
                cmd +="sudo "
            cmd += "%s " % register_tool
            cmd += "--name=%s -- --interval=%s" % (tool,interval)
            self.logger.debug('PBench Start : Command : %s' % cmd)
            if not self.tools.run_cmd(cmd) :
                self.logger.error("Issue registering tool.")
                return False
        return self.register_remote_tools()

    def get_results_dir(self,prefix):
        cmd="find /var/lib/pbench-agent/ -name \"*%s*\" -print"%prefix
        return self.tools.run_cmd(cmd)

    def register_remote_tools(self):
        tool="register-tool"
        register_tool=self.tools.find_cmd(tool)
        interval = self.config['browbeat']['pbench']['interval']
        if len(self.hosts.options('hosts')) > 0 :
            for node in self.hosts.options('hosts'):
                cmd = ""
                as_sudo = self.config['browbeat']['sudo']
                if as_sudo :
                    cmd +="sudo "
                cmd = ""
                for tool in self.config['browbeat']['pbench']['tools'] :
                    cmd = ""
                    if as_sudo :
                        cmd +="sudo "
                    cmd += "%s " % register_tool
                    cmd += "--name=%s --remote=%s -- --interval=%s" % (tool,node,interval)
                    self.logger.debug('PBench register-remote: Command : %s' % cmd)
                    if not self.tools.run_cmd(cmd) :
                        self.logger.error("Issue registering tool.")
                        return False
        return True

    # PBench Stop Tools
    def stop_pbench(self,sudo=False):
        tool="stop-tools"
        stop_tool=self.tools.find_cmd(tool)
        cmd = ""
        if sudo :
            cmd +="sudo "
        cmd = "%s" % stop_tool
        self.logger.info('PBench Stop : Command : %s' % cmd)
        self.tools.run_cmd(cmd)
        return True

    # Move Results
    def move_results(self,sudo=False):
        tool="move-results"
        move_tool=self.tools.find_cmd(tool)
        cmd = ""
        if sudo :
            cmd +="sudo "
        cmd = "%s" % move_tool
        self.logger.info('PBench move-results : Command : %s' % cmd)
        self.tools.run_cmd(cmd)
        return True
