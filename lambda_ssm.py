from __future__ import print_function
from boto3.session import Session

import json
import urllib
import boto3
import zipfile
import tempfile
import botocore
import traceback
import logging
import gzip
import time

from io import BytesIO
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ssm_client = boto3.client('ssm')
code_pipeline = boto3.client('codepipeline')

def find_artifact(artifacts, name):
    """Finds the artifact 'name' among the 'artifacts'
    
    Args:
        artifacts: The list of artifacts available to the function
        name: The artifact we wish to use
    Returns:
        The artifact dictionary found
    Raises:
        Exception: If no matching artifact is found
    
    """
    for artifact in artifacts:
        if artifact['name'] == name:
            return artifact
            
    raise Exception('Input artifact named "{0}" not found in event'.format(name))
    
def put_job_failure(job, message):
    """Notify CodePipeline of a failed job
    
    Args:
        job: The CodePipeline job ID
        message: A message to be logged relating to the job status
        
    Raises:
        Exception: Any exception thrown by .put_job_failure_result()
    
    """
    logger.info('Putting job failure')
    logger.debug(message)
    code_pipeline.put_job_failure_result(jobId=job, failureDetails={'message': message, 'type': 'JobFailed'})
 
def setup_s3_client(job_data):
    """Creates an S3 client
    
    Uses the credentials passed in the event by CodePipeline. These
    credentials can be used to access the artifact bucket.
    
    Args:
        job_data: The job data structure
        
    Returns:
        An S3 client with the appropriate credentials
        
    """
    key_id = job_data['artifactCredentials']['accessKeyId']
    key_secret = job_data['artifactCredentials']['secretAccessKey']
    session_token = job_data['artifactCredentials']['sessionToken']
    
    session = Session(aws_access_key_id=key_id,
        aws_secret_access_key=key_secret,
        aws_session_token=session_token)
    return session.client('s3', config=botocore.client.Config(signature_version='s3v4'))

def get_artifacts(s3, artifact, bucket_pipe, folder_pipe):
    """Gets the code artifact
    
    Downloads the artifact from the S3 artifact store to a temporary file
    then extracts the zip and upload to the pipeline bucket
    
    Args:
        artifact: The artifact to download
        bucket_pipe: The Pipeline bucket to upload artifacts
        folder_pipe: The Pipeline folder to upload artifacts
        
    Raises:
        Exception: Any exception thrown while downloading the artifact or unzipping it
    
    """

    bucket = artifact['location']['s3Location']['bucketName']
    key = artifact['location']['s3Location']['objectKey']
    tmp_file = tempfile.NamedTemporaryFile(delete=False)

    with open(tmp_file.name, 'wb') as f:
        s3.download_fileobj(bucket, key, f)
    
    s3_pipe = boto3.client('s3')
    s3_pipe.upload_file(
        tmp_file.name, 
        bucket_pipe, 
        folder_pipe + '/artifacts.zip')

    #     with zipfile.ZipFile(tmp_file.name, 'r') as zip:
    #         return zip.read(file_in_zip)   

    # s3_pipe.upload_fileobj(
    #     Fileobj=gzip.GzipFile(
    #         None,
    #         'rb',
    #         fileobj=BytesIO(
    #             s3.get_object(Bucket=bucket, Key=key)['Body'].read())),
    #     Bucket=bucket_pipe,
    #     Key=folder_pipe)

def get_user_params(job_data):
    """Decodes the JSON user parameters and validates the required properties.
    
    Args:
        job_data: The job data structure containing the UserParameters string which should be a valid JSON structure
        
    Returns:
        The JSON parameters decoded as a dictionary.
        
    Raises:
        Exception: The JSON can't be decoded or a property is missing.
        
    """
    try:
        # Get the user parameters which contain the stack, artifact and file settings
        user_parameters = job_data['actionConfiguration']['configuration']['UserParameters']
        decoded_parameters = json.loads(user_parameters)
            
    except Exception as e:
        # We're expecting the user parameters to be encoded as JSON
        # so we can pass multiple values. If the JSON can't be decoded
        # then fail the job with a helpful message.
        raise Exception('UserParameters could not be decoded as JSON')
    
    if 'bucket' not in decoded_parameters:
        # Validate that the bucket is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the bucket name')
    
    if 'sns' not in decoded_parameters:
        # Validate that the sns arn is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the sns arn')
    
    if 'template' not in decoded_parameters:
        # Validate that the ec2 template is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the ec2 template name')
    
    return decoded_parameters

def create_ec2_instance(template, job_id):
    try:
        response = ec2_client.run_instances(LaunchTemplate={
                'LaunchTemplateId': template
            },
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'job_id',
                            'Value': job_id
                        }
                    ]
                }
            ],
            MinCount=1,
            MaxCount=1
        )
    except ClientError as e:
        raise e
    else:
        return response['Instances'][0]
        
def lambda_handler(event, context):
    """The Lambda function handler
    
    If a continuing job then checks the CloudFormation stack status
    and updates the job accordingly.
    
    If a new job then kick of an update or creation of the target
    CloudFormation stack.
    
    Args:
        event: The event passed by Lambda
        context: The context passed by Lambda
        
    """
    try:
        logger.debug(event)
        
        # Extract the Job ID
        job_id = event['CodePipeline.job']['id']
        
        # Extract the Job Data 
        job_data = event['CodePipeline.job']['data']
        
        # Extract the params
        params = get_user_params(job_data)
        
        # Get the list of artifacts passed to the function
        artifacts = job_data['inputArtifacts']
        
        # Get the artifact details
        artifact_data = find_artifact(artifacts, 'SourceArtifact')

        # Get S3 client to access artifact with
        s3 = setup_s3_client(job_data)

        # Get artifacts to be used into build process
        get_artifacts(s3, artifact_data, params['bucket'], job_id)

        # Kick off ec2 to build artifacts
        instance_info = create_ec2_instance(params['template'], job_id)
        
        # Wait for connection
        if instance_info is not None:
            ec2_instance = instance_info["InstanceId"]
            logger.info(f'Launched EC2 Instance {ec2_instance}')
            logger.info(f'    VPC ID: {instance_info["VpcId"]}')
            logger.info(f'    Private IP Address: {instance_info["PrivateIpAddress"]}')
            logger.info(f'    Current State: {instance_info["State"]["Name"]}')
    
            while True:
                response = ssm_client.get_connection_status(Target=ec2_instance)
                ec2_status = response['Status']
                if ec2_status == 'connected':
                    logger.info(f'EC2 Instance ready - Connection State: {ec2_status}')
                    break
                else:
                    logger.info(f'Waiting for EC2 Instance - Connection State: {ec2_status}')
                    time.sleep(10)
    
            response = ssm_client.send_command(
                InstanceIds=[ec2_instance],
                DocumentName="AWS-RunRemoteScript",
                Parameters={
                    "sourceType":["S3"],
                    "sourceInfo":["{\"path\":\"https://codecommit-535519225013-us-west-2.s3-us-west-2.amazonaws.com/build_ssm.bat\"}"],
                    "commandLine":[("build_ssm.bat %s %s %s %s %s" % (
                        params['bucket'], 
                        job_id,
                        params['sns'],
                        ec2_instance,
                        instance_info["PrivateIpAddress"]))],
                    "workingDirectory":[""],
                    "executionTimeout":["3600"]
                },
                CloudWatchOutputConfig={
                    'CloudWatchOutputEnabled': True
                })
            
            #The job sucess will be informed by the ec2 build process

    except Exception as e:
        # If any other exceptions which we didn't expect are raised
        # then fail the job and log the exception message.
        logger.info('Function failed due to exception.') 
        logger.error(e)
        traceback.print_exc()
        put_job_failure(job_id, 'Function exception: ' + str(e))
      
    logger.info('Function complete.')   
    return "Complete."
