Feature: Device QA ARTF (Automated regression testing framework) in behaviour-driven development
  As an IoT tester,
  I want to test the features of the firmware location at either
  - build (local file in build directory),
  - S3 (AWS S3 bucket) or,
  - artifact (GitLab CI)
  So that the devices are validated for
  - flashing firmware by serial
  - updating firmware by OTA through AWS.


  @hub_halo_test @halo_test @hub_flash_ref
  Scenario: Hub flash reference firmware
    Given Hub is connected to COM port, get reference firmware, and device flash is erased
    When the device is flashed with the firmware through COM port
    Then the device is successfully updated to the firmware and work properly


  @hub_halo_test @halo_test @halo_flash_ref
  Scenario: Halo flash reference firmware
    Given Halo is connected to COM port, get reference firmware, and device flash is erased
    When the device is flashed with the firmware through COM port
    Then the device is successfully updated to the firmware and work properly
    Then configure the devices to get firmware from artifacts


#  @hub_halo_test @hub_flash
#  Scenario: Flash hub test
#    Given Hub is connected to COM port
#    When the device is flashed with the firmware through COM port
#    Then the device is successfully updated to this test firmware and work properly


  @hub_halo_test @halo_test @hub_halo_flash
  Scenario: Flash devices test
    Given both devices are connected to COM port
    When the device with updated repo is flashed with the latest firmware through COM port
    Then  the device is successfully updated to the firmware and work properly


  @hub_halo_test @hub_halo_ota @hub_test @hub_ota
  Scenario: Hub OTA test
    Given Hub is connected to COM port
    And the device works properly
    When the latest firmware is updated to the Hub through OTA
    Then the device is successfully updated to the firmware and work properly
    And OTA image is verified as valid
    And In AWS the OTA job will be done successfully


  @hub_halo_test @halo_test @hub_halo_ota @halo_ota
  Scenario: Halo OTA test
    Given both devices are connected to COM port
    And both devices work properly
    When the latest firmware is updated to the Halo through OTA
    Then the device is successfully updated to the firmware and work properly
    And OTA image is verified as valid
    And In AWS the OTA job will be done successfully


#  @hub_halo_test @regress_hub_ota
#  Scenario Outline:
#    Given Hub is connected to COM port and get <flash_firmware> from AWS S3 bucket
#    And the device is flashed with the firmware through COM port and works properly
#    When the <ota_firmware> is updated to the Hub through OTA
#    Then the device is successfully updated to the firmware and work properly
#    And OTA image is verified as valid
#    And In AWS the OTA job will be done successfully
#    Examples:
#    | flash_firmware                                    | ota_firmware                        |
#    | hub_app_v2.0.2_0df97a8+_97197fb5_sha256-12909.bin | artifact                            |
#    | hub_app_v2.0.2_604cb4a+_23d7742a_sha256-16709.bin | artifact                            |


  @fleet_Hub_test @regress_hub_ota
  Scenario Outline: Fleet Hub OTA test
    Given Devices has been setup and online
    When the latest firmware is updated to the thing group through OTA <thing_group> <file_type>
    Then In AWS the OTA job for fleet will be done successfully <thing_group> <file_type>

     Examples:
       | thing_group       | file_type  |
       | Spiral_test     | 1          |

  @fleet_Halo_test @regress_hub_ota
  Scenario Outline: Fleet Halo OTA test
     Given Devices has been setup and online
     When the latest firmware is updated to the thing group through OTA <thing_group> <file_type>
     Then In AWS the OTA job for fleet will be done successfully <thing_group> <file_type>

     Examples:
       | thing_group            | file_type  |
       | Fleet_devices_halo     | 2          |







