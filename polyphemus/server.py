import flask
from flask import request
import os
from io import StringIO
import csv
from . import workproc
from .db import JobDB, ARCHIVE_NAME, NotFoundError, BadJobError
from datetime import datetime
import re
from . import state
import json
import git

INSTANCE_DIR = os.path.abspath(os.environ.get('POLYPHEMUS_DIR') or 'instance')

# Our Flask application.
app = flask.Flask(__name__, instance_path=INSTANCE_DIR, instance_relative_config=True)

# Configuration. We include some defaults and allow overrides.
app.config.from_object('polyphemus.config_default')
app.config.from_pyfile('polyphemus.cfg', silent=True)

# Use worker threads by default in development.
if app.config['WORKER_THREADS'] is None:
    app.config['WORKER_THREADS'] = (app.env == 'development')

# Connect to our database.
db = JobDB(app.instance_path)

STATUS_STRINGS = {
    state.UPLOAD: "Uploaded",
    state.UNPACK: "Unpacking",
    state.HLS_FINISH: "Start Executing",
    state.MAKE: "Start make",
    state.MAKE_PROGRESS: "Makeing",
    state.AFI_START: "Start AFI",
    state.AFI: "Generating AFI",
    state.RUN: "Running",
    state.DONE: "Done",
    state.FAIL: "Failed",
}


def git_commit_sha():
    sha = git.Repo().head.object.hexsha[:7]
    link = "{}/commit/{}".format(app.config['GH_REPO'], sha)
    return sha, link


def _get(job_name):
    """Get a job by name, or raise a 404 error."""
    try:
        return db.get(job_name)
    except NotFoundError:
        flask.abort(404, 'Job {} not found.'.format(job_name))
    except BadJobError:
        flask.abort(410, 'Job {} is malformed.'.format(job_name))


def _unpad(s):
    """Remove padding zeroes from a formatted date string."""
    return re.sub(r'(^|\s)0+', r'\1', s)



@app.template_filter('dt')
def _datetime_filter(value, withtime=True):
    """Format a timestamp (given as a float) as a human-readable string.
    `withtime` indicates whether this should be just a day or a day with
    a time.
    """
    if not value:
        return ''
    dt = datetime.fromtimestamp(value)

    fmt = '%Y-%m-%d'
    if withtime:
        fmt += ' %H:%M'
    return _unpad(dt.strftime(fmt))


@app.before_first_request
def start_workers():
    """Start the workers, if necessary.

    In WORKER_THREADS mode, start a bunch of threads *in this process*
    to do the work. This is *not safe* if there might be multiple server
    processes or threads, which will all start different copies of the
    worker threads!

    Otherwise, the worker process needs to be run separately. We do not
    try to launch it ourselves.
    """
    if app.config['WORKER_THREADS']:
        proc = workproc.WorkProc(app.instance_path, db)
        proc.start()


def notify_workers(jobname):
    """Notify the workers that a new job has been created.

    Unless we're in WORKER_THREADS mode, we send a message to the
    (already-running) workproc.
    """
    if not (app.config['WORKER_THREADS'] or app.config['POLL_MODE']):
        workproc.notify(app.instance_path, jobname)


def get_config(values):
    """Get the job configuration options specified by data in the given
    form values.
    """
    config = {}
    for key, typ in app.config['CONFIG_OPTIONS'].items():
        config[key] = typ(values.get(key, ''))
    return config


def list_files(job_name):
    """Generate the paths to all the job's files.
    """
    job_dir = db.job_dir(job_name)
    for dirpath, _, filenames in os.walk(job_dir):
        dp = os.path.relpath(dirpath, job_dir)
        for fn in filenames:
            if not fn.startswith('.'):
                yield os.path.join(dp, fn)


# Upload a job to the server.
@app.route('/jobs', methods=['POST'])
def add_job():
    config = get_config(request.values)

    # Get the code either from an archive or a parameter.
    if 'file' in request.files:
        file = request.files['file']

        # Check that the file has an allowed extension.
        _, ext = os.path.splitext(file.filename)
        if ext[1:] not in app.config['UPLOAD_EXTENSIONS']:
            return 'invalid extension {}'.format(ext), 400

        # Create the job and save the archive file.
        with db.create(state.UPLOAD, config) as name:
            file.save(ARCHIVE_NAME + ext)
        notify_workers(name)

    else:
        return 'missing code or file', 400

    # In the browser, redirect to the detail page. Otherwise, just
    # return the job name.
    if request.values.get('browser'):
        return flask.redirect(flask.url_for('show_job', name=name))
    else:
        return name


@app.route('/jobs.csv')
def jobs_csv():
    output = StringIO()
    writer = csv.DictWriter(
        output,
        ['name', 'started', 'state'],
    )
    writer.writeheader()

    for job in db._all():
        writer.writerow({
            'name': job['name'],
            'started': job['started'],
            'state': job['state'],
        })

    csv_data = output.getvalue()
    return csv_data, 200, {'Content-Type': 'text/csv'}


# Get the list of all jobs.
@app.route('/')
def jobs_html():
    sha, link = git_commit_sha()
    return flask.render_template(
        'joblist.html',
        commit={'sha': sha, 'link': link},
        jobs=db._all(),
        status_strings=STATUS_STRINGS,
    )


# Either get the job information (through the GET route) or update the job
# information (through the POST route).
@app.route('/jobs/<name>.html', methods=['GET', 'POST'])
def show_job(name):
    job = _get(name)

    # Possibly update the job.
    if request.method == 'POST':
        # Is this a job state change request?
        if 'state' in request.form:
            new_state = request.form['state']
            db.set_state(job, new_state)
            notify_workers(job['name'])

        # Is this a name change request?
        elif 'hwname' in request.form:
            new_name = request.form['hwname']
            job['config']['hwname'] = new_name
            db.log(job['name'], 'hwname changed to {}'.format(new_name))
            db._write(job)

        else:
            flask.abort(500, 'Unknown POST request.')


    # Construct regex for interesting words
    interest_regex = re.compile('|'.join(app.config['IMPORTANT_WORDS']), re.I)

    # Get the last few lines and interesting lines from the log.
    log_filename = db._log_path(name)
    lines = app.config['LOG_PREVIEW_LINES']
    try:
        with open(log_filename) as f:
            file = list(f)
            log_lines = file[-lines:]
            interesting_lines = [l for l in file if interest_regex.search(l)]
    except IOError:
        log_lines = []
        interesting_lines = []

    return flask.render_template(
        'job.html',
        job=job,
        json_config=json.dumps(job['config'], indent=4, sort_keys=True),
        status_strings=STATUS_STRINGS,
        update_states=state.UNLOCKED_STATES,
        log=''.join(log_lines),
        interesting=''.join(interesting_lines),
    )


@app.route('/jobs/<name>/log.txt')
def job_log(name):
    filename = db._log_path(name)
    return flask.send_file(filename)


@app.route('/jobs/<name>/files.html')
def job_files_html(name):
    job = _get(name)
    return flask.render_template(
        'files.html',
        job=job,
        files=list(list_files(name)),
    )


@app.route('/jobs/<name>')
def get_job(name):
    job = _get(name)
    return flask.jsonify(job)


@app.route('/jobs/<name>/files')
def get_job_files(name):
    _get(name)
    return flask.jsonify(list(list_files(name)))


@app.route('/jobs/<name>/files/<path:filename>')
def job_file(name, filename):
    # Make sure this job actually exists.
    _get(name)

    # Check whether we should force a plain-text MIME type.
    _, ext = os.path.splitext(filename)
    mime = 'text/plain' if ext[1:] in app.config['TEXT_EXTENSIONS'] else None

    # Send the file.
    return flask.send_from_directory(db.job_dir(name), filename, mimetype=mime)
