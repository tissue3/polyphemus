import threading
import os
import time
import json
import glob
import re

from .stages_common import work, task_config, update_make_conf
from .worker_common import stage_unpack
from . import state
from .db import CODE_DIR

from .worker_f1 import stage_f1_make_compile, stage_f1_make_copy, stage_afi, stage_f1_fpga_execute
from .worker_sdsoc import stage_sdsoc_make, stage_zynq_fpga_execute

# Strings corresponding to stages known to workers.
KNOWN_STAGES = {
    "unpack": stage_unpack,
    "make_compile_f1": stage_f1_make_compile,
    "make_copy_f1": stage_f1_make_copy,
    "make_sdsoc": stage_sdsoc_make,
    "afi": stage_afi,
    "exec_f1": stage_f1_fpga_execute,
    "exec_zynq": stage_zynq_fpga_execute,
}


class WorkThread(threading.Thread):
    """A base class for all our worker threads, which run indefinitely
    to process tasks in an appropriate state.

    The thread takes the database and configuration dictionaries as well
    as a function to which these will be passed. When the thread runs,
    the function is invoked repeatedly, indefinitely.
    """

    def __init__(self, db, config, func):
        self.db = db
        self.config = config
        self.func = func
        super(WorkThread, self).__init__(daemon=True)

    def run(self):
        while True:
            self.func(self.db, self.config)

def default_work_stages(config):
    """List of functions for the configured toolchain.
    """

    # Toolchain dependent stage configuration
    stages = [stage_unpack] 
    stages += [stage_f1_make_compile, stage_f1_make_copy] if config['TOOLCHAIN'] == 'f1' else [stage_sdsoc_make]

    if config['TOOLCHAIN'] == 'f1':
        stages += stage_afi, stage_f1_fpga_execute
    else:
        stages += [stage_zynq_fpga_execute]

    stages += [stage_make for i in range(config['PARALLELISM_MAKE'] - 1)]

    return stages


def work_threads(stages, config, db):
    """Return a list of (unstarted) Thread objects from a list of stage functions
    """
    return [WorkThread(db, config, stage) for stage in stages]
