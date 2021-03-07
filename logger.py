import datetime
import os

# To use:
#   import logger
#
#   # Logs to <.py name>.log; e.g. main.py.log
#   log = logger.Log(__file__) 
#
#   log.plog("This message prints to STDOUT and logs to file")
#   log.log("This message logs to file")

class Log:
  def __init__(self, name):
    # Creates a "log" directory to log into
    log_dir = "log"
    self.log_location = "log/{}.log".format(name)
    if not os.path.exists(log_dir):
      os.makedirs(log_dir)

  # Helper function
  def write_to_log(self, out):
    f = open(self.log_location, 'a')
    f.write(out)
    f.close()
  # Helper function
  def prepend_datetime(self, s):
    return "[{}] {}".format(now(), s)

  # Prints to STDOUT and log to file
  # Does not manage log size, be careful when using
  def plog(self, s):
    out = self.prepend_datetime(s)
    print(out) # STDOUT
    self.write_to_log(out) # Logfile

  # Only log to file 
  # Does not manage log size, be careful when using 
  def log(self, s):
    out = self.prepend_datetime(s)
    self.write_to_log(out) # Logfile

# Returns current datetime
def now():
  return str(datetime.datetime.now())
