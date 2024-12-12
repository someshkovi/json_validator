# DEFAULT LOGGING IDs
INFO = "INFO"
WARN = "WARN"
ERROR = "ERROR"
CRITICAL = "CRITICAL"
DEBUG = "DEBUG"
TRACE = "TRACE"

def log(message: str, log_id: str = INFO):
    print(message)