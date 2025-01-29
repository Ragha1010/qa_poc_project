import logging
import os
import glob
from behave import fixture, use_fixture
from tiny_test_fw import Env
from tiny_test_fw.TinyFW import DefaultEnvConfig
from ttfw_idf import IDFDUT
from ttfw_esys import ESYSDUT
from ttfw_esys.ESYSApp import SiApp
from ttfw_esys.ESYSApp import SiAppPreBuilt
from ttfw_esys.ESYSApp import SiArtifact


@fixture
def environment_hub_and_halo(context):
    env_config = DefaultEnvConfig.get_default_config()
    env_config["dut"] = IDFDUT
    env_config["dut"] = ESYSDUT
    if context.firm_location == 'S3':
        env_config["app"] = SiAppPreBuilt
    if context.firm_location == 'build':
        env_config["app"] = SiApp
    if context.firm_location == 'artifact':
        env_config["app"] = SiArtifact
    context.environment = Env.Env(**env_config)


def before_all(context):
    context.config.setup_logging(level=logging.INFO)
    context.firm_location = "artifact"
    # context.firm_location = "build"
    # context.firm_location = "S3"
    # Define the USB to serial chipset VID of hub and halo to identify them during port detection
    context.hub_vid = 1027
    context.halo_vid = 4292

    if context.firm_location == "build" or context.firm_location == "S3":
        context.project_name = "si_app"
        context.firm_version = "2.1.1"
        context.firm_name = "si_app.bin"
        context.sha256 = None

    if context.firm_location == "artifact":
        if 'job_id' not in context.config.userdata:
            assert False, "job_id has to be specified in behave argument for artifact"
        if 'gitlab_proj' not in context.config.userdata:
            assert False, "gitlab_proj (Gitlab Project name) has to be specified in behave argument for artifact"
        else:
            context.gitlab_proj = context.config.userdata['gitlab_proj']
            if context.gitlab_proj == 'sentry-interface':
                context.project_name = "si_app"
            if context.gitlab_proj == 'sentry-reader':
                context.project_name = "sr_app"

    if context.project_name == "si_app" or context.project_name == "sr_app":
        use_fixture(environment_hub_and_halo, context)


def after_all(context):
    if context.firm_location != "build":
        files = os.path.join('build', '*.bin')
        for file in glob.glob(files):
            os.remove(file)



