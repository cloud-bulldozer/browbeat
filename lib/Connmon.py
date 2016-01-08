from Tools import *

class Connmon :
    def __init__(self,config):
        self.logger = logging.getLogger('browbeat.Connmon')
        self.config = config
        self.tools = Tools(self.config)
        return None

    # Start connmond
    def start_connmon(self):
        self.stop_connmon()
        tool="connmond"
        connmond=self.tools.find_cmd(tool)
        if not connmond :
            self.logger.error("Unable to find {}".format(tool))
        as_sudo = self.config['browbeat']['sudo']
        cmd = ""
        if as_sudo :
            cmd +="sudo "
        cmd += "screen -X -S connmond kill"
        self.tools.run_cmd(cmd)
        self.logger.info("Starting connmond")
        cmd = ""
        cmd +="{} --config /etc/connmon.cfg > /tmp/connmond 2>&1 &".format(connmond)
        return self.tools.run_cmd(cmd)

    # Stop connmond
    def stop_connmon(self):
        self.logger.info("Stopping connmond")
        return self.tools.run_cmd("pkill -9 connmond")

    # Create Connmon graphs
    def connmon_graphs(self,result_dir,test_name):
        cmd="python graphing/connmonplot.py {}/connmon/{}.csv".format(result_dir,
                                                                            test_name)
        return self.tools.run_cmd(cmd)

    # Move connmon results
    def move_connmon_results(self,result_dir,test_name):
        path = "%s/connmon" % result_dir
        if not os.path.exists(path) :
            os.mkdir(path)
        return shutil.move("/tmp/connmon_results.csv",
                    "{}/connmon/{}.csv".format(result_dir,test_name))
