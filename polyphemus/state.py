# Jobs can be in two types of states: Locked (marked with <>) and Unlocked.
# When several workers are running in parallel, they grab a lock on one of the
# unlocked jobs they are capable of running and start executing them.
#
#
#       UPLOAD
#         |
#      <UNPACK>
#         |
#        MAKE-------------------+
#         |                     |
#         |               <MAKE_COMPILE> (F1 only)
#         |                     |
#         |                COPY_START (F1 only)
#  <MAKE_PROGRESS>              |
#         |               <MAKE_COPY> (F1 only)
#         |                     |
#         |                 AFI_START (F1 only)
#         |                     |
#         +---------------<AFI> (F1 only)
#         |
#     HLS_FINISH
#         |
#       <RUN>
#         |
#   +-----+-----+
#   |           |
# DONE         FAIL


UPLOAD = "uploaded"
UNPACK = "unpacking"
MAKE = "make"
MAKE_PROGRESS = "makeing"
MAKE_COMPILE = "make_compiling"
COPY_START = "starting_compile"
MAKE_COPY = "make_copying"
HLS_FINISH = "hlsed"
AFI_START = "starting_AFI"
AFI = "generating_AFI"
RUN = "fpga_executing"
DONE = "done"
FAIL = "failed"

UNLOCKED_STATES = MAKE, COPY_START, AFI_START, HLS_FINISH, DONE, FAIL
