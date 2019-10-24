# Name of the deployment
NAME = "Polyphemus"

# Github repository
GH_REPO = "https://github.com/cucapra/polyphemus"

# The extensions to allow for uploaded code archives.
UPLOAD_EXTENSIONS = ['zip']

# A prefix command to use *before* the invocations of Xilinx tools. For
# example, if your deployment needs to execute the Xilinx tools on a different
# machine or a different Docker container, a deployment could use this prefix
# to send these commands there.
HLS_COMMAND_PREFIX = []

# Spawn threads inside the server process for the workers (instead of
# using a separate worker process). The default (None) means True in the
# development environment and False in production.
WORKER_THREADS = False

# Assume the workers are using continous polling instead of socket-based
# communication
POLL_MODE = True #False

# The number of jobs to process in parallel in the "make" stage (which is the
# expensive, long-running one).
PARALLELISM_MAKE = 1

# Filename extensions to send as plain text for job file viewing.
TEXT_EXTENSIONS = [
    'c',
    'cpp',
    's',
    'log',
    'jou',
    'tcl',
    'd',
    'dat',
    'rpt',
    'est',
]

# All curl options come from strings. Convert strings to bool.
def str_to_bool(x):
    return not (x == '0' or x == '')

# Configuration options allowed during job creation. Each option has a
# conversion function (i.e., type) used to translate the request value.
CONFIG_OPTIONS = {
    'estimate': str_to_bool,
    'skipexec': str_to_bool,
    'make': str_to_bool,
    'directives': str,
    'hwname': str,
    'platform': str,
    'mode': str,
}

# The name to use for compiled executables.
EXECUTABLE_NAME = 'exe'

# The number of (recent) lines of the log to show on job pages.
LOG_PREVIEW_LINES = 32

# The timeouts for running the initial compilation step and for running
# the synthesis step (or running an opaque Makefile), the latter of
# which has to be really long because synthesis is so slow.
COMPILE_TIMEOUT = 120
SYNTHESIS_TIMEOUT = 20000

# Polyphemus currently supports two backend toolchains: Xilinx's SDSoC
# (for Zynq processors) and SDAccel (for AWS F1). Set this to "f1" for
# deployment on F1; leave it as anything else for the SDSoC workflow.
TOOLCHAIN = 'f1'

# Options for SDSoC/Zynq.
DEFAULT_PLATFORM = 'zed'  # Use the "platform" job config option to override.

# Options for SDAccel/F1.
DEFAULT_F1_MODE = 'sw_emu'  # Use the "mode" job config option to override.
S3_BUCKET = 'test-bucket-1025132741'
S3_DCP = 'DCPs'  # dcp-folder-name
S3_LOG = 'SDAccel_log'  # logs-folder-name
AFI_CHECK_INTERVAL = 300  # Sleep time between each AFI status check.

# Keywords for "interesting" lines in the log. Case and location insensitive.
# Can use regex for these.
IMPORTANT_WORDS = [
    "warn",
    "error",
    "ignore", "ignoring"
]

# Configuration variables to look for when running the make stage. Can use
# regex for these. Case insensitive.
MAKE_CONF_VARS = [
    "device", "platform", "estimate", "target", "directives", "target_freq"
    # "\S*cxx\S*", "\S*flags\S*"
]
