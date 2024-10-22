# coding: utf-8

import os
import sys
import shutil

from textwrap import dedent
from traitlets import Bool, Instance, Type, Unicode
from traitlets.config.application import catch_config_error, default

from .baseapp import NbGrader

from ..api import Gradebook
from ..utils import find_all_files, check_directory, find_all_notebooks
import zipfile

aliases = {
    'log-level': 'Application.log_level'
}

flags = {
    'debug': (
        {'Application': {'log_level': 'DEBUG'}},
        "set log level to DEBUG (maximize logging output)"
    )
}


class ZipReleaseFeedbackApp(NbGrader):

    name = u'nbgrader-zip-release'
    description = u"Release assignment's feedback to archive (zip file)."

    aliases = aliases
    flags = flags

    examples = """
        Releases assignment submissions to archives (zip) files
        to be uploaded to a LMS. For the usage of instructors.
    """

    dirname_suffix = Unicode(
        '_assignsubmission_file_',
        help=dedent(
            """
            The suffix to be appended to the dirnames of each student.
            """
        )
    ).tag(config=True)  

    solution_prefix = Unicode(
        'solution-',
        help=dedent(
            """
            The prefix to be appended to the solution notebook if included.
            """
        )
    ).tag(config=True)    

    output_directory = Unicode(
        'uploaded',
        help=dedent(
            """
             The name of the directory that will contain the assignment feedback zip archive.
            """
        )
    ).tag(config=True)

    include_source = Bool(
        True,
        help=dedent(
            """
            Whether or not to include the source in the feedback zip archive.
            """
        )
    ).tag(config=True)

    @catch_config_error
    def initialize(self, argv=None):
        cwd = os.getcwd()
        if cwd not in sys.path:
            # Add cwd to path so that custom plugins are found and loaded
            sys.path.insert(0, cwd)

        super(ZipReleaseFeedbackApp, self).initialize(argv)

        # set assignemnt and course
        if len(self.extra_args) == 1:
            self.coursedir.assignment_id = self.extra_args[0]
        elif len(self.extra_args) > 2:
            self.fail("Too many arguments")
        elif self.coursedir.assignment_id == "":
            self.fail(
                "Must provide assignment name:\n"
                "nbgrader zip_release_feedbakc ASSIGNMENT"
            )

    def _mkdirs_if_missing(self, path):
        if not check_directory(path, write=True, execute=True):
            self.log.warning("Directory not found. Creating: {}".format(path))
            os.makedirs(path)

    def start(self):
        super(ZipReleaseFeedbackApp, self).start()        

        self._mkdirs_if_missing(self.output_directory)
        with Gradebook(self.coursedir.db_url, self.coursedir.course_id) as gb, zipfile.ZipFile(os.path.join(f"{self.output_directory}", f"{self.coursedir.assignment_id}-feedback.zip"), 'w', zipfile.ZIP_DEFLATED) as archive:
            students = [s.id for s in gb.students]
            for student_id in students:
                source_path = self.coursedir.format_path(
                    self.coursedir.feedback_directory, student_id, self.coursedir.assignment_id)
                feedback_files = list(filter(lambda f: f.endswith('.html'), find_all_files(source_path)))
                if feedback_files:
                    dirname = f"{student_id}{self.dirname_suffix}"
                    for fn in feedback_files:
                        archive.write(fn, arcname=os.path.join(dirname, os.path.basename(fn)))     
                    if self.include_source:
                        # search for the source notebooks, to be included in the feedback
                        source_file_path = self.coursedir.format_path(self.coursedir.source_directory, '.', self.coursedir.assignment_id)
                        for fn in os.listdir(source_file_path):
                            if fn.endswith('.ipynb'):
                                archive.write(os.path.join(source_file_path, fn), arcname=os.path.join(dirname, f"{self.solution_prefix}{os.path.basename(fn)}"))

        


