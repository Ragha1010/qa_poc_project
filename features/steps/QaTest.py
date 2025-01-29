import logging
import time
import fleet
import features.steps.device_lib
from device_lib.aws_iot import AWSSimplifiedIoTOTA

from behave import given, when, then
import ttfw_esys
import re
from tiny_test_fw import DUT
from ttfw_esys.ESYSDUT import ESYSHubDut
from ttfw_esys.ESYSDUT import ESYSHaloDut
from tiny_test_fw import Env
from tiny_test_fw.TinyFW import DefaultEnvConfig
from ttfw_esys import ESYSDUT
from ttfw_esys.ESYSApp import SiApp
from ttfw_esys.ESYSApp import SiAppPreBuilt
from ttfw_esys.ESYSApp import SiArtifact

from features.steps.fleet import Fleet

logging.basicConfig(
    level=logging.INFO,
)


def erase_device(context):
    logging.info('Erase device flash memory')
    context.dut.erase_flash_partition('bootloader')
    context.dut.erase_flash_partition('partition_table')
    context.dut.erase_flash_partition('otadata')
    context.dut.erase_flash_partition('factory')
    context.dut.erase_flash_partition('ota_0')
    context.dut.erase_flash_partition('ota_1')

def get_hub_halo_dut(context):
    env = context.environment
    try:
        dut = env.get_dut(None, None, context, dut_class=ttfw_esys.ESP32DUT)
    except ValueError as err:
        logging.info("Fail to connect device through serial port:" + str(err))
        assert False, err
    if isinstance(dut, ESYSHubDut):
        context.hub_dut = dut
    if isinstance(dut, ESYSHaloDut):
        context.halo_dut = dut


@given(u'Both devices are connected to COM port')
def step_impl(context):
    # check if devices are connected at before
    devices_to_connect = 0
    env = context.environment
    dut = env.check_dut("Hub")
    if dut is not None:
        context.hub_dut = dut
    else:
        devices_to_connect += 1
    dut = env.check_dut("Halo")
    if dut is not None:
        context.halo_dut = dut
    else:
        devices_to_connect += 1

    while devices_to_connect > 0:
        get_hub_halo_dut(context)
        devices_to_connect -= 1

    time.sleep(1)
    context.hub_dut.reset()
    context.halo_dut.reset()
    time.sleep(2)


@given(u'Hub is connected to COM port')
def step_impl(context):
    # check if hub is connected at before
    env = context.environment
    dut = env.check_dut("Hub")
    if dut is not None:
        context.hub_dut = dut
    else:
        get_hub_halo_dut(context)
        if hasattr(context, 'hub_dut') is False:
            get_hub_halo_dut(context)
    context.dut = context.hub_dut


@given(u'Halo is connected to COM port')
def step_impl(context):
    # check if halo is connected at before
    env = context.environment
    dut = env.check_dut("Halo")
    if dut is not None:
        context.halo_dut = dut
    else:
        get_hub_halo_dut(context)
        if hasattr(context, 'halo_dut') is False:
            get_hub_halo_dut(context)
            if hasattr(context, 'halo_dut') is False:
                assert False, 'Failed to detect Halo'
    context.dut = context.halo_dut


@when(u'the device with updated repo is flashed with the latest firmware through COM port')
def step_impl(context):
    context.dut = None
    if context.gitlab_proj == 'sentry-interface':
        context.dut = context.hub_dut
    elif context.gitlab_proj == 'sentry-reader':
        context.dut = context.halo_dut
    else:
        assert False, 'Invalid gitlab_proj argument: ' + context.gitlab_proj

    context.dut.flash_device()


@then(u'the device is successfully updated to the firmware and work properly')
def step_impl(context):
    context.dut.flash_verify()


@then(u'both devices release the COM port')
def step_impl(context):
    context.hub_dut.close()
    context.halo_dut.close()


@then(u'the device releases the COM port')
def step_impl(context):
    context.dut.close()


@given(u'both devices work properly')
def step_impl(context):
    context.hub_dut.run_verify()
    context.halo_dut.run_verify()


@given(u'the device works properly')
def step_impl(context):
    context.dut.run_verify()
@given (u'Devices has been setup and online')
def step_given_some_precondition(context):
    pass

@when (u'the latest firmware is updated to the thing group through OTA {thing_group} {filetype}')
def step_impl(context,thing_group, filetype):
    fleet = Fleet(thing_group)
    context.jobid = fleet.esys_ota_launch_fleet(thing_group,filetype)


@then (u'In AWS the OTA job for fleet will be done successfully {thing_group} {filetype}')
def step_impl(context, thing_group, filetype):
    fleet = Fleet()
    fleet.ota_Fleet_aws_verify(context.jobid, thing_group, filetype)


@when(u'the latest firmware is updated to the Hub through OTA')
def step_impl(context):
    context.dut.ota_start()


@when(u'the latest firmware is updated to the Halo through OTA')
def step_impl(context):
    context.dut = context.halo_dut
    context.dut.ota_start(context.hub_dut)


@then(u'OTA image is verified as valid')
def step_impl(context):
    context.dut.ota_image_verify()


@then(u'In AWS the OTA job will be done successfully')
def step_impl(context):
    context.dut.ota_aws_verify()


@given(u'Hub is run and connected to AWS')
def step_impl(context):
    context.hub_dut.run_verify()


@when(u'the device is flashed with the firmware through COM port')
def step_impl(context):
    context.dut.flash_device()


@given(u'{device} is connected to COM port and then obtain {flash_firmware} from AWS S3 bucket')
def step_impl(context, device, flash_firmware):
    env = context.environment
    env.app_cls = SiAppPreBuilt
    context.firm_location = 'S3'
    context.firm_name = flash_firmware
    if flash_firmware == 'ARTF_ref_apps':
        context.firm_ref_app = 'ARTF_ref_apps'
    else:
        context.firm_ref_app = 'None'
    if device == 'Hub':
        context.execute_steps('given Hub is connected to COM port')
    elif device == 'Halo':
        context.execute_steps('given Halo is connected to COM port')
    else:
        logging.info("Invalid device is called in statement:" + device +
                     " is connected to COM port and get {flash_firmware} from AWS S3 bucket")
        assert False
    bin_file_name = context.dut.app.bin_app_file[6:]
    if bin_file_name != context.firm_name:
        app_path = context.dut.app.app_name
        context.dut.app = env.app_cls(app_path, None, None, context)


@given(u'Hub is connected to COM port and get {flash_firmware} from AWS S3 bucket')
def step_impl(context, flash_firmware):
    context.execute_steps('given Hub is connected to COM port and then obtain ' + flash_firmware + ' from AWS S3 bucket')


@given(u'the device is flashed with the firmware through COM port and works properly')
def step_impl(context):
    context.dut.flash_device()
    context.dut.flash_verify()


@when(u'the {ota_firmware} is updated to the Hub through OTA')
def step_impl(context, ota_firmware):
    env = context.environment
    if ota_firmware == 'artifact':
        env.app_cls = SiArtifact
        context.firm_location = 'artifact'

    elif re.findall(".bin$", ota_firmware):
        context.firm_name = ota_firmware
        env.app_cls = SiAppPreBuilt
        context.firm_location = 'S3'

    else:
        assert False, 'Unknown OTA firmware'

    app_path = context.dut.app.app_name
    serial = context.dut.app.serial
    context.dut.app = env.app_cls(app_path, None, None, context)
    context.dut.app.serial = serial
    context.dut.ota_start()


@given(u'Hub is connected to COM port, get reference firmware, and device flash is erased')
def step_impl(context):
    context.execute_steps('given Hub is connected to COM port and then obtain ' +
                          'ARTF_ref_apps from AWS S3 bucket')
    erase_device(context)


@given(u'Halo is connected to COM port, get reference firmware, and device flash is erased')
def step_impl(context):
    context.execute_steps('given Halo is connected to COM port and then obtain ' +
                          'ARTF_ref_apps from AWS S3 bucket')
    erase_device(context)


@then(u'configure the devices to get firmware from artifacts')
def step_impl(context):
    env = context.environment
    env.app_cls = SiArtifact
    context.firm_location = 'artifact'

    # Only the project under test get binary from GitLab artifact.  Another one just used the golden one in AWS S3
    if context.gitlab_proj == 'sentry-interface':
        dut = env.check_dut("Hub")
        if dut is not None:
            context.hub_dut = dut
        context.dut = context.hub_dut
        app_path = context.dut.app.app_name
        context.dut.app = env.app_cls(app_path, None, 'esp32', context)

    if context.gitlab_proj == 'sentry-reader':
        dut = env.check_dut("Halo")
        if dut is not None:
            context.halo_dut = dut
        context.dut = context.halo_dut
        app_path = context.dut.app.app_name
        context.dut.app = env.app_cls(app_path, None, 'esp32', context)



