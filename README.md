# ARTF 
Device QA ARTF (Automated regression testing framework) is designed based on python behave package. 
It is applicable for testing binary from:
* GitLab CI/CD generated in build-job stage. Then behave test is carried out in test-job stage
* Local build folder
* AWS S3 bucket

## File Structures
### QaTest.feature
The feature file to define the testing behavior. It is divided into several scenarios, each one consists of a test unit  
It is written in Gherkin language
### QaTest.py
It is in “steps” directory with Python step implementations for the scenarios defined in `QaTest.feature`
### Environment.py
Define the python code to be run first at the beginning of the test.  It is used to set the testing environment.

## Python packages
Please install the following packages beforehand
* pip install junit_xml
* pip install netifaces
* pip install PyYAML
* pip install pyserial
* pip install python-gitlab
* pip install pexpect

Note: Please don't install esptool, as it stops python behave program runs properly.

## Usage
User has to define the following items:
### Environment.py
Edit environment.py, under 'features' directory, for the following parameters
#### `context.firm_location`
* Please specify firmware binary location either `artifact` (GitLab CI/CD), `S3` (in AWS) or `build` (in local 'build' folder)
* If `context.firm_location` is `artifact`, it will get the GitLab artifact from the build job stage in the pipeline
* * If `context.firm_location` is `S3` or `build`, please specified following parameters:
#### `context.project_name`
* `si_app` or `sr_app`, which is the one displayed in firmware serial message `Project name:`
#### `context.firm_version`
* version of the firmware like `2.0.0`, which is the one displayed in firmware serial message `App version:`
#### `context.firm_name`
* binary file name

### Behave parameters
* If IDE is PyCharm, edit behave parameters under Edit Configuration -> Parameters
* If it's run in .gitlab-ci.yml, the parameters are defined in python behave command 
#### --tags
* It is used to determine which scenario of QaTest.feature file to be run
* `--tags=hub_halo_test`: run all scenarios defined in `QaTest.feature`
* `--tags=hub_test`: only runs hub flash device test and hub OTA test
* `--tags=halo_test`: only runs halo flash device test and halo OTA test


If `context.firm_location` is `artifact` , it has to add two parameter in .gitlab-ci.yml
* `-D job_id=$BUILD_JOB_ID`, to access the right artifact of the job ID  
* `-D gitlab_proj='sentry-interface'`, to define the project to get the artifact
* `-D partition_version=y`, where y is 4 for new partition table v4.  If this parameter doesn't include, the old partition table v3 will be used.
 
## Note
* Whenever any AWS service has to be used in PC development environment, please run `aws-mfa` to enter token first to gain authorization




