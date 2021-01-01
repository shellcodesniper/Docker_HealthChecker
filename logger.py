import os
import boto3
import logging
from aws_logging_handlers.S3 import S3Handler
from aws_logging_handlers.Kinesis import KinesisHandler
  
DEFAULT_FORMATTER = logging.Formatter('[%(asctime)s] %(filename)s:%(lineno)d} %(levelname)s - %(message)s')

def get_logger(logger_name):
  return logging.getLogger(logger_name)

#!time_rotation : 12*60*60 : 12시간마다 새로운 파일 생성
#!max_file_size_bytes : 100*1024**2 : 100MB


def create_logger(logger_name, formatter, ACCESS_KEY, SECRET_KEY, REGION_NAME, bucket, log_name='test_logger', log_root='logs', server_id='USE_IP',service_name='SERVICE_NAME', time_rotation=12*60*60, max_file_size_bytes=100*1024**2):
  logger = logging.getLogger(logger_name)
  log_root = os.path.join(log_root, server_id, service_name)
  print ('LOG_ROOT:', log_root)

  # s3_client = boto3.client(
  #     's3',
  #     aws_access_key_id=ACCESS_KEY,
  #     aws_secret_access_key=SECRET_KEY,
  # )

  # s3 = boto3.resource(
  #     's3',
  #     aws_access_key_id=ACCESS_KEY,
  #     aws_secret_access_key=SECRET_KEY,
  #     region_name=REGION_NAME
  # )

  bucket = "kuuwang"
  s3_handler = S3Handler(
    log_name, bucket, workers=3,
    log_root=log_root,
    aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION_NAME,
    time_rotation=time_rotation,
    max_file_size_bytes=max_file_size_bytes,
    encryption_options={})

  s3_handler.setFormatter(formatter)

  logger.setLevel(logging.DEBUG)
  logger.addHandler(s3_handler)

  return logger

def test_logger(logger):
  for i in range(0, 100000):
      logger.info("test info message")
      logger.warning("test warning message")
      logger.error("test error message")

  logging.shutdown()


if(__name__ == "__main__"):
  ACCESS_KEY = 'AKIATHKUHZRQADDGIYP6'
  SECRET_KEY = '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'
  REGION_NAME = 'ap-northeast-2'
  formatter = logging.Formatter('[%(asctime)s] %(filename)s:%(lineno)d} %(levelname)s - %(message)s')
  logger = create_logger('main_logger', formatter, ACCESS_KEY, SECRET_KEY, REGION_NAME, bucket='kuuwang', log_name='test_log', log_root='logs',server_id='USE_IP', time_rotation=5, max_file_size_bytes=1*1024**2)
  logger = get_logger('main_logger')
  test_logger(logger)
