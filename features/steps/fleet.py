

import sys
from features.steps.device_lib.aws_iot import AWSSimplifiedIoTOTA
from features.steps.device_lib.aws_iot import AWSIoTOTA
import gitlab
import logging
import os


try:
    import gitlab_api
except ImportError:
    gitlab_api = None

import logging
import os
import gitlab_api

class Fleet:
    def __init__(self, thing_group=None):
        self.aws_inst = AWSSimplifiedIoTOTA(thing_group=thing_group)

    def get_binary_latest_job_id(self,file_type):
        project_mapping = {
                1: 'sentry-interface',
                2: 'sentry-reader'
            }
        project_name = project_mapping.get (file_type)
        gitlab_inst = gitlab_api.Gitlab(project_name=project_name)
        # As the job list is too long, we only need the latest 50 ones.
        jobs = gitlab_inst.project.jobs.list(page=1, per_page=50, order_by='created_at', sort='desc', get_all=False)
        job_id = 0
        for job in jobs:
            if hasattr(job, 'artifacts_file') and job.name == 'uat-build-job' and job.status == 'success':
                job_id = job.id
                break
        # Download into current directory and zip extract into build directory
        self.bin_app_file = gitlab_inst.download_artifacts(job_id, '.')
        logging.info ("The binary file name found from gitlab {}".format (self.bin_app_file))
        if self.bin_app_file:
                return self.bin_app_file
        else:
            logging.error ("Failed to download artifacts or Failed to retrieve the latest job.")
            return None


    def esys_ota_launch_fleet(self, Thing_group, file_type):
        """
        Launch OTA and monitor the number of OTA blocks remaining
        @Thing_group: Thing group for OTA deployment
        @file_type: 1 for Hub, 2 for Halo
        """
        logging.info("Starting...")
        logging.info("Params: {} {}".format(Thing_group, file_type))
        self.bin_app_file = self.get_binary_latest_job_id(int(file_type))
        file_path = os.path.abspath(self.bin_app_file)
        logging.info('Starting OTA with binary file:' + self.bin_app_file[6:])
        job_ids = self.aws_inst.launch_fota(thing_group=Thing_group, app_bin=self.bin_app_file[6:], update_to=None, timeout=5, fileType=file_type)
        logging.info("aws_ota_job_id generated: {}".format(job_ids))
        return job_ids[0]

    def ota_Fleet_aws_verify(self, job_id, thing_group, filetype):
        logging.info('ota..aws job_id {}, thing_group {}'.format(job_id,thing_group))
        result = self.aws_inst.complete_check_fleet(job_id=job_id,thing_group=thing_group, filetype=filetype)
        logging.info(f'AWS OTA result: {result}')
        if result != 'SUCCEEDED':
            jobdescriptionstatus = self.aws_inst.status_check_fleet (job_id)
            if jobdescriptionstatus == 'COMPLETED':
                logging.info('OTA job cannot be cancelled as it has already completed.')
            else:
                cancel_response = self.aws_inst.cancel_ota_job(job_id)
                logging.info('OTA job is cancelled')
            error_message = 'OTA is Failed'
            assert False, 'OTA is Failed'