from aws_logging_handlers.S3 import MAX_FILE_SIZE_BYTES
from datetime import datetime, timedelta
import requests
import parser
import docker
import os
import time
import service_manager
import logging
import logger
import atexit
import io
import threading
import pycron
from termcolor import colored

RUN_IN_DOCKER = os.environ.get('RUN_IN_DOCKER', False)
DEBUG_MODE = (str(os.environ.get('DEBUG_MODE', 'no')).lower().count('yes') > 0)
VERBOSE_MODE = (str(os.environ.get('VERBOSE_MODE', 'no')).lower().count('yes') > 0)
print ("DEBUG MODE : {}".format(DEBUG_MODE))
print ("VERBOSE MODE : {}".format(VERBOSE_MODE))
CHECK_POOL = bool(str(os.environ.get('CHECK_POOL', 'no')).lower().count('yes') > 0)


if (not os.path.isfile('/app/docker-compose-origin.yml')):
  print('docker-compose-origin.yml 파일을 /app/ 에 마운트 해주셔야 합니다.')
  os._exit(0)

config = parser.CONFIGURE
SERVER_ID = str(config["기본"]["SERVER_ID"].strip())
if(SERVER_ID == "" or SERVER_ID == "USE_IP"):
  SERVER_ID = requests.get('https://api.kuuwang.com/ip').text

USE_CUSTOM_DOCKER = bool(str(config["기본"]["도커모드"]).lower().count('yes') > 0)

#! LOGGING
IS_LOGGING = bool(str(config['기본']['LOGGING']).lower().count('yes') > 0)
BUCKET = ''
LOG_ROOT = 'logs'
ACCESS_KEY = ''
SECRET_KEY = ''
REGION_NAME = ''
FORMATTER = logging.Formatter('[%(asctime)s] %(filename)s:%(lineno)d} %(levelname)s - %(message)s')
MAX_FILE_SIZE_BYTES = 100*1024**2
TIME_ROTATION = 12*60*60
HEALTHCHECKER_LOGNAME = 'HEALTHCHECKER'
MAIN_LOGGER = None
REPEAT_TIME = 0.01

USE_CRON = False
CRON_TEXT = ''
try:
  USE_CRON = bool(str(config["기본"]["USE_CRON"]).lower().count('yes') > 0)
  CRON_TEXT = str(config["기본"]["CRON_TEXT"]).strip()
except Exception as E:
  print ('NO CRON')
  print (E)
  pass

if (IS_LOGGING):
  BUCKET = str(config["LOGGING"]["BUCKET"].strip())
  LOG_ROOT = str(config["LOGGING"]["ROOT_PATH"].strip())
  ACCESS_KEY = str(config["LOGGING"]["ACCESS_KEY"].strip())
  SECRET_KEY = str(config["LOGGING"]["SECRET_KEY"].strip())
  REGION_NAME = str(config["LOGGING"]["REGION_NAME"].strip())
  HEALTHCHECKER_LOGNAME = str(config["LOGGING"]["HEALTHCHECKER_LOGNAME"].strip())
  MAX_FILE_SIZE_BYTES = int(config["LOGGING"]["MAX_FILE_SIZE_MB"].strip()) * (1024 ** 2)
  TIME_ROTATION = int(config["LOGGING"]["TIME_ROTATION"].strip())
  MAIN_LOGGER = logger.create_logger("MAIN_LOGGER", FORMATTER, ACCESS_KEY, SECRET_KEY, REGION_NAME, bucket=BUCKET, log_name='healthchecker_log',
                                     log_root=LOG_ROOT, server_id=SERVER_ID, service_name=HEALTHCHECKER_LOGNAME, max_file_size_bytes=MAX_FILE_SIZE_BYTES, time_rotation=TIME_ROTATION)
  

def main_print(*args, **kwargs):
  global IS_LOGGING, MAIN_LOGGER, VERBOSE_MODE
  if IS_LOGGING:
    try:
      with io.StringIO() as F:
        print(" ".join(map(str, args)), file=F)
        output = F.getvalue()
        mode = kwargs.get('mode', 'debug')
        if(mode == 'debug'):
          MAIN_LOGGER.debug(output)
        elif(mode == 'info'):
          MAIN_LOGGER.info(output)
        elif(mode == 'error'):
          MAIN_LOGGER.error(output)
    except:
      print("Logging Error")
  if VERBOSE_MODE:
    color_pick = kwargs.get('color', 'cyan')
    color_attr = kwargs.get('color_attr', ['bold'])
    print(colored(" ".join(map(str, args)), color=color_pick, attrs=color_attr))



#! ETC
MANAUL_AUTH = bool(str(config["기본"]["도커허브로그인정보제공"]).lower().count('yes') > 0)
SLEEP_TIME = int(config['기본']['확인주기'])
BURNUP_TIME = int(config['기본']['BURNUP대기시간'])
USE_NGINX = bool(str(config['기본']['NGINX사용']).lower().count('yes') > 0)
CURRENT_CONTAINER_NAME = str(config['기본']['현재실행중인컨테이너이름']).strip()
UPDATE_REPEAT_INTERVAL = int(config['기본']['업데이트확인_주기'].strip())


def exit_handler():
  try:
    main_print('\n'*100)
  except:
    pass
  try:
    time.sleep(1)
  except:
    pass
  try:
    main_print('*********** 프로그램 종료 실행한 도커 컨테이너 정리 ***********\n'*50)
  except:
    pass
  try:
    time.sleep(1)
  except:
    pass
  if(USE_NGINX):
    main_print('NGINX 사용함으로 설정되었으므로, NGINX 컨테이너도 초기화 합니다.')
    try:
      os.system("docker kill nginx  > /dev/null 2>&1")
      # os.system("docker rm nginx  > /dev/null 2>&1")
    except:
      pass
  for service in config["컨테이너"]:
    SERVICE_CONTAINER_NAME = str(config["컨테이너"][service])
    try:
      os.system("docker kill {}  > /dev/null 2>&1".format(SERVICE_CONTAINER_NAME))
      # os.system("docker rm {}  > /dev/null 2>&1".format(SERVICE_CONTAINER_NAME))
    except:
      pass
  main_print('docker compose 종료')
  try:
    os.system("docker-compose -f /app/docker-compose.yml down")
  except:
    pass
  # main_print ('다음 업데이트를 위하여 이미지 정리')
  # try:
  #   os.system("docker image prune -a -f")
  # except:
  #   pass
  # if (IS_LOGGING):
  #   logging.shutdown()


atexit.register(exit_handler)

if (USE_CUSTOM_DOCKER):
  main_print('도커모드 활성화로, 도커접속정보를 이용하여 도커에 연결시도합니다.')
  try:
    client = docker.DockerClient(base_url=str(config['도커설정']['접속정보']))
    main_print('도커모드로 접속이 완료되었습니다.')
  except:
    main_print("도커와 통신할수 없습니다.도커 접속정보 혹은 도커 볼륨 설정을 확인해주시기 바랍니다.")
    os._exit(0)
else:
  client = docker.from_env()

if(MANAUL_AUTH):
  main_print('로그인정보 제공으로 인하여 도커허브 로그인을 진행합니다.')
  USERNAME = str(config["도커허브"]["아이디"]).strip()
  PASSWORD = str(config["도커허브"]["비밀번호"]).strip()
  REGISTRY_URL = 'registry.docker.io'
  client.login(USERNAME, PASSWORD)
  if RUN_IN_DOCKER:
    main_print ("DOCKER 내부에서 실행중이므로, 로그인을 진행합니다.")
    main_print(os.system('docker login -u {} -p {}'.format( USERNAME, PASSWORD)))
  main_print('도커허브 로그인이 완료되었습니다.')

SERVICE_NAME_LIST = []
SERVICE_DICT = {}
REGISTERED_CONTAINER_DICT = {}

for service in config["컨테이너"]:
  SERVICE_NAME_LIST = list(set(SERVICE_NAME_LIST))

  SERVICE_MASTER_NAME = (str(service)[::-1].split('_', 1)[1])[::-1].lower()
  SERVICE_CONTAINER_NAME = str(config["컨테이너"][service])
  SERVICE_LEVEL = (str(service).split('_')[-1]).lower()
  if(SERVICE_MASTER_NAME in SERVICE_NAME_LIST):
    SERVICE_DICT[SERVICE_MASTER_NAME].register_container(level=SERVICE_LEVEL, container_name=SERVICE_CONTAINER_NAME, service_name=service)
    REGISTERED_CONTAINER_DICT[SERVICE_CONTAINER_NAME] = SERVICE_MASTER_NAME
  else:
    SERVICE_NAME_LIST.append(SERVICE_MASTER_NAME)
    
    env_var_name_target_port = ''
    env_var_name_target_container = ''
    env_var_name_listen_port = ''
    env_default_target_port = ''
    env_default_target_container = ''
    env_default_listen_port = ''
    for envConfig in config["컨테이너_NGINX"]:
      envService = (str(envConfig)[::-1].split('_', 1)[1])[::-1].lower()
      if(envService.strip() == SERVICE_MASTER_NAME.lower().strip()):
        purpose = str(envConfig).split('_')[-1].upper().strip()
        value = config["컨테이너_NGINX"][envConfig]
        if(purpose == "TARGETPORT"):
          env_var_name_target_port = value
        elif(purpose == "TARGETCONTAINER"):
          env_var_name_target_container = value
        elif(purpose == "LISTENPORT"):
          env_var_name_listen_port = value

    for defaultConfig in config["컨테이너_기본설정"]:
      defaultService = (str(defaultConfig)[::-1].split('_', 1)[1])[::-1].lower()
      if(defaultService.strip() == SERVICE_MASTER_NAME.lower().strip()):
        purpose = str(defaultConfig).split('_')[-1].upper().strip()
        value = config["컨테이너_기본설정"][defaultConfig]
        if(purpose == "TARGETPORT"):
          env_default_target_port = value
        elif(purpose == "TARGETCONTAINER"):
          env_default_target_container = value
        elif(purpose == "LISTENPORT"):
          env_default_listen_port = value
        
    ENVDICT = {
      'TARGETPORT': env_var_name_target_port,
      'TARGETCONTAINER': env_var_name_target_container,
      'LISTENPORT': env_var_name_listen_port,
    }

    DEFAULTDICT = {
      'TARGETPORT': env_default_target_port,
      'TARGETCONTAINER': env_default_target_container,
      'LISTENPORT': env_default_listen_port,
    }

    service_logger = None
    if(IS_LOGGING):
      service_logger = logger.create_logger("{}_{}".format(SERVICE_MASTER_NAME,'MAIN'), FORMATTER, ACCESS_KEY, SECRET_KEY, REGION_NAME, bucket=BUCKET, log_name='log',
                                            log_root=LOG_ROOT, server_id=SERVER_ID, service_name=os.path.join(SERVICE_MASTER_NAME, 'main'), max_file_size_bytes=MAX_FILE_SIZE_BYTES, time_rotation=TIME_ROTATION)
        
    SERVICE_DICT[SERVICE_MASTER_NAME] = service_manager.Service(
        name=SERVICE_MASTER_NAME, client=client, ENVDICT=ENVDICT, DEFAULTDICT=DEFAULTDICT, checkInterval=UPDATE_REPEAT_INTERVAL, currentContainer=CURRENT_CONTAINER_NAME, isLogging=IS_LOGGING, logger=service_logger)
    SERVICE_DICT[SERVICE_MASTER_NAME].register_container(
        level=SERVICE_LEVEL, container_name=SERVICE_CONTAINER_NAME, service_name=service)
    REGISTERED_CONTAINER_DICT[SERVICE_CONTAINER_NAME] = SERVICE_MASTER_NAME


  # main_print ("서비스가 이미 실행중 혹은 컨테이너에 존재하는경우, 죽이고 삭제 진행. 컨테이너 이름 : [{}]".format(SERVICE_CONTAINER_NAME))
  main_print ("서비스가 이미 실행중 혹은 컨테이너에 존재하는경우, kill. 컨테이너 이름 : [{}]".format(SERVICE_CONTAINER_NAME))
  try:
    os.system("docker kill {} > /dev/null 2>&1".format(SERVICE_CONTAINER_NAME))
    # os.system("docker rm {}  > /dev/null 2>&1".format(SERVICE_CONTAINER_NAME))
  except:
    pass


if(USE_NGINX):
  main_print ('NGINX 사용함으로 설정되었으므로, NGINX 컨테이너도 초기화 합니다.')
  try:
    os.system("docker kill nginx  > /dev/null 2>&1")
    # os.system("docker rm nginx  > /dev/null 2>&1")
  except:
    pass
# os.system("docker image prune -a -f")


# check_call(['docker-compose', '-f /app/docker-compose.yml', 'up'], stdout=DEVNULL, stderr=STDOUT)
# os.system('docker-compose -f /app/docker-compose.yml up > /dev/null 2>&1 &')



with open('/app/docker-compose-origin.yml', 'rt') as F:
  composeData = F.read()
  for SERVICE_KEY in SERVICE_DICT.keys():
    if(SERVICE_DICT[SERVICE_KEY].DEFAULTDICT['TARGETCONTAINER'].strip() != ''):
      env = SERVICE_DICT[SERVICE_KEY].currentEnvironment
      for key in env.keys():
        composeData = composeData.replace('${' + key.strip() + '}', env[key])
        if DEBUG_MODE:
          main_print(('${' + key.strip() + '}', env[key]))
  with open('/app/docker-compose.yml', 'wt') as FO:
    FO.write(composeData)

if (CHECK_POOL):
  print('\n'*5)
  main_print('CHECK_POOL 모드로 업데이트 및 healthchecking은 실행되지않음을 유의해주시기 바랍니다.', color='red', color_attr=['bold', 'blink'])
  print('\n'*5)
  time.sleep(3)
  os.system("docker-compose -f /app/docker-compose.yml up --build")
else:
  os.system("docker-compose -f /app/docker-compose.yml up --build -d")


print ('\n'*100)
main_print ('첫번째 도커 컨테이너가 온라인이 될때까지 반복 실행 시작', color_attr=['bold', 'blink'])

REGISTERED_CONTAINER_KEYS = list(REGISTERED_CONTAINER_DICT.keys())
count = 0
returnFlag = False
while True:
  if(count > 60 or returnFlag):
    break
  main_print ('{} 컨테이너 존재여부 확인 {}/60<최대>'.format(REGISTERED_CONTAINER_KEYS[0], count), color='yellow', color_attr=['blink'])
  for container in client.containers.list():
    container_name = container.name
    if(container_name.lower().count(REGISTERED_CONTAINER_KEYS[0].strip()) > 0):
      main_print ('첫번째 컨테이너가 존재하고 시작됨을 감지하였으니 본 로직으로 돌아갑니다.', color='red', color_attr=['bold', 'blink'])
      time.sleep(1)
      print ('\n'*100)
      returnFlag = True
      break
  count += 1
  time.sleep(1)

for service in SERVICE_DICT.keys():
  main_print(f"SERVICE {service}의 MASTER, SLAVE, ROLLBACK를 시작합니다.",color_attr=['bold', 'blink'])
  SERVICE_DICT[service].burnup_container()

main_print ("BURNUP!!! {}초 대기".format(BURNUP_TIME), color_attr=['bold'])
time.sleep(BURNUP_TIME)

main_print('=== DOCKER SERVICE 목록 추출 ===', color_attr=['blink'])
for container in client.containers.list():
  container_name = container.name
  if container_name in REGISTERED_CONTAINER_KEYS:
    main_print(f'container_name:[{container_name}]에 대한 기본정보 등록 및 관리 Class 생성', color_attr=['bold'])
    container_image = container.attrs['Config']['Image']
    last_hash = (client.images.get_registry_data(container_image)).id
    SERVICE_MASTER_NAME = REGISTERED_CONTAINER_DICT[container_name]
    SERVICE_DICT[SERVICE_MASTER_NAME].set_value('last_hash', last_hash, container_name=container_name)

def repeat_checking():
  for SERVICE_KEY in SERVICE_DICT.keys():
    try:
      SERVICE_DICT[SERVICE_KEY].repeat_checker(SERVICE_DICT)
    except Exception as E:
      main_print(f'repeat_checking에러 SERVICE_KEY:{SERVICE_KEY}', mode='error', color='red', color_attr=['bold'])
      main_print(E, mode='error')
def update_checking():
  for SERVICE_KEY in SERVICE_DICT.keys():
    try:
      SERVICE_DICT[SERVICE_KEY].update_checker(SERVICE_DICT)
    except Exception as E:
      main_print(f'update_checking에러 SERVICE_KEY:{SERVICE_KEY}', mode='error', color='red', color_attr=['bold'])
      main_print(E, mode='error')

def repeat_update_docker():
  global client
  try:
    for container in client.containers.list():
      container_name = container.name
      container_id = container.id
      container_hash = container.attrs['Image']
      container_image = container.attrs['Config']['Image']
      # if (DEBUG_MODE):
      #   main_print('ID: {} 컨테이너 이름 : {} IMAGE : {} HASH : {}'.format(container_id, container_name, container_image, container_hash))
      if container_name in REGISTERED_CONTAINER_KEYS:
        SERVICE_MASTER_NAME = REGISTERED_CONTAINER_DICT[container_name]
        SERVICE_DICT[SERVICE_MASTER_NAME].update_info(
            container_name, container_id, container_hash, container_image)
    # ! 컨테이너 업데이트 ( 재시작시 id 변경되기때문에 )
  except Exception as E:
    main_print ("CONTAINER UPDATE_INFO ERROR")
    main_print (E)
    main_print ("UPDATE_INFO 오류는 docker api 쪽 문제가 다분함,\n 도커 접속정보 재설정 진행.", color='red', color_attr=['bold', 'blink'])
    client = docker.DockerClient(base_url=str(config['도커설정']['접속정보']))
    for service in SERVICE_DICT.keys():
      main_print(f"SERVICE {service}의 MASTER, SLAVE, ROLLBACK를 시작합니다.", color_attr=['bold', 'blink'])
      SERVICE_DICT[service].docker_api_reassign(client)

next_container_check = time.time() + SLEEP_TIME
next_repeat_check = time.time() + SLEEP_TIME
next_update_check = (time.time() + (SLEEP_TIME * UPDATE_REPEAT_INTERVAL)) if USE_CRON == False else time.time() + (SLEEP_TIME * 2 + 3)

main_print('도커 정보 업데이트 (MAIN_PROCESS)', color_attr=['bold', 'blink'])
repeat_update_docker()
#! docker 정보를 업데이트 해주도록 ( 뭐가 먼저 실행될지 모르니까 !)
main_print('첫번째 REPEAT CHECK 실행', color_attr=['bold', 'blink'])
repeat_checking()
#! docker 정보 다음으로는 repeat checking 업데이트!

progress = 0
while True:
  import random
  if(progress > 100):
    progress = 100
  print(colored(f'----- LOADING {progress}% -----', color='green', attrs=['bold']))
  if(progress == 100):
    main_print('START MAIN ROUTINE')
    break
  progress += random.randint(0, 20)
  time.sleep((random.randint(0, 100) / 100))

while True:
  try:
    current_time = time.time()
    
    if((current_time - next_container_check) > 0):
      main_print('DOCKER_INFO_UPDATE [INTERVAL]')
      next_container_check = current_time + SLEEP_TIME
      repeat_update_docker()
      thread = threading.Thread(target=repeat_update_docker)
      thread.start()

    if((current_time - next_repeat_check) > 0):
      main_print('REPEAT CHECKER')
      next_repeat_check = current_time + SLEEP_TIME
      thread = threading.Thread(target=repeat_checking)
      thread.start()


    if(USE_CRON == True):
      if(pycron.is_now(CRON_TEXT) and ((current_time - next_update_check) > 0)):
        main_print('UPDATE CHECK [CRON_TAB]')
        next_update_check = current_time + 60
        thread = threading.Thread(target=update_checking)
        thread.start()
    elif((current_time - next_update_check) > 0):
      main_print('UPDATE CHECK [INTERVAL]')
      next_update_check = current_time + SLEEP_TIME
      thread = threading.Thread(target=update_checking)
      thread.start()
      
    time.sleep(REPEAT_TIME)

  except KeyboardInterrupt:
    main_print('EXIT!')
    exit_handler()
    os._exit(0)
  except Exception as E:
    main_print(E, mode='error')
