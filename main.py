import parser
import docker
import os
import time
import service_manager
import threading
import atexit


RUN_IN_DOCKER = os.environ.get('RUN_IN_DOCKER', False)
DEBUG_MODE = bool(str(os.environ.get('DEBUG_MODE', 'no')).lower().count('yes') > 0)
CHECK_POOL = bool(str(os.environ.get('CHECK_POOL', 'no')).lower().count('yes') > 0)


if (not os.path.isfile('/app/docker-compose-origin.yml')):
  print('docker-compose-origin.yml 파일을 /app/ 에 마운트 해주셔야 합니다.')
  os._exit(0)

config = parser.CONFIGURE
USE_CUSTOM_DOCKER = bool(str(config["기본"]["도커모드"]).lower().count('yes') > 0)
MANAUL_AUTH = bool(str(config["기본"]["도커허브로그인정보제공"]).lower().count('yes') > 0)
SLEEP_TIME = int(config['기본']['확인주기'])
BURNUP_TIME = int(config['기본']['BURNUP대기시간'])
USE_NGINX = bool(str(config['기본']['NGINX사용']).lower().count('yes') > 0)
CURRENT_CONTAINER_NAME = str(config['기본']['현재실행중인컨테이너이름']).strip()


def exit_handler():
  try:
    print('\n'*100)
  except:
    pass
  try:
    time.sleep(1)
  except:
    pass
  try:
    print('*********** 프로그램 종료 실행한 도커 컨테이너 정리 ***********\n'*50)
  except:
    pass
  try:
    time.sleep(1)
  except:
    pass
  if(USE_NGINX):
    print('NGINX 사용함으로 설정되었으므로, NGINX 컨테이너도 초기화 합니다.')
    try:
      os.system("docker kill nginx  > /dev/null 2>&1")
    except:
      pass
  for service in config["컨테이너"]:
    SERVICE_CONTAINER_NAME = str(config["컨테이너"][service])
    try:
      os.system("docker kill {}  > /dev/null 2>&1".format(SERVICE_CONTAINER_NAME))
    except:
      pass


atexit.register(exit_handler)

if (USE_CUSTOM_DOCKER):
  print('도커모드 활성화로, 도커접속정보를 이용하여 도커에 연결시도합니다.')
  try:
    client = docker.DockerClient(base_url=str(config['도커설정']['접속정보']))
    print('도커모드로 접속이 완료되었습니다.')
  except:
    print("도커와 통신할수 없습니다.도커 접속정보 혹은 도커 볼륨 설정을 확인해주시기 바랍니다.")
    os._exit(0)
else:
  client = docker.from_env()

if(MANAUL_AUTH):
  print('로그인정보 제공으로 인하여 도커허브 로그인을 진행합니다.')
  USERNAME = str(config["도커허브"]["아이디"]).strip()
  PASSWORD = str(config["도커허브"]["비밀번호"]).strip()
  REGISTRY_URL = 'registry.docker.io'
  client.login(USERNAME, PASSWORD)
  if RUN_IN_DOCKER:
    print ("DOCKER 내부에서 실행중이므로, 로그인을 진행합니다.")
    print(os.system('docker login -u {} -p {}'.format( USERNAME, PASSWORD)))
  print('도커허브 로그인이 완료되었습니다.')

SERVICE_NAME_LIST = []
SERVICE_DICT = {}
REGISTERED_CONTAINER_DICT = {}

for service in config["컨테이너"]:
  SERVICE_NAME_LIST = list(set(SERVICE_NAME_LIST))

  SERVICE_MASTER_NAME = (str(service)[::-1].split('_', 1)[1])[::-1].lower()
  SERVICE_CONTAINER_NAME = str(config["컨테이너"][service])
  SERVICE_LEVEL = (str(service).split('_')[-1]).lower()
  if(SERVICE_MASTER_NAME in SERVICE_NAME_LIST):
    SERVICE_DICT[SERVICE_MASTER_NAME].register_container(
        level=SERVICE_LEVEL, container_name=SERVICE_CONTAINER_NAME, service_name=service)
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
        
    SERVICE_DICT[SERVICE_MASTER_NAME] = service_manager.Service(
        name=SERVICE_MASTER_NAME, client=client, ENVDICT=ENVDICT, DEFAULTDICT=DEFAULTDICT)
    SERVICE_DICT[SERVICE_MASTER_NAME].register_container(
        level=SERVICE_LEVEL, container_name=SERVICE_CONTAINER_NAME, service_name=service)
    REGISTERED_CONTAINER_DICT[SERVICE_CONTAINER_NAME] = SERVICE_MASTER_NAME


  print ("서비스가 이미 실행중 혹은 컨테이너에 존재하는경우, 죽이고 삭제 진행. 컨테이너 이름 : [{}]".format(SERVICE_CONTAINER_NAME))
  try:
    os.system("docker kill {} > /dev/null 2>&1".format(SERVICE_CONTAINER_NAME))
    os.system("docker rm {}  > /dev/null 2>&1".format(SERVICE_CONTAINER_NAME))
  except:
    pass


if(USE_NGINX):
  print ('NGINX 사용함으로 설정되었으므로, NGINX 컨테이너도 초기화 합니다.')
  try:
    os.system("docker kill nginx  > /dev/null 2>&1")
    os.system("docker rm nginx  > /dev/null 2>&1")
  except:
    pass


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
          print(('${' + key.strip() + '}', env[key]))
  with open('/app/docker-compose.yml', 'wt') as FO:
    FO.write(composeData)

if (CHECK_POOL):
  os.system("docker-compose -f /app/docker-compose.yml up --build")
else:
  os.system("docker-compose -f /app/docker-compose.yml up --build -d")

if (DEBUG_MODE):
  print("NGINX DEFAULT.CONF 삭제 & 재시작")
os.system("docker exec {} docker exec nginx rm /etc/nginx/conf.d/default.conf".format(CURRENT_CONTAINER_NAME))
os.system("docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build nginx")


print ('\n'*100)
print ('첫번째 도커 컨테이너가 온라인이 될때까지 반복 실행 시작')

REGISTERED_CONTAINER_KEYS = list(REGISTERED_CONTAINER_DICT.keys())
count = 0
returnFlag = False
while True:
  if(count > 60 or returnFlag):
    break
  print ('{} 컨테이너 존재여부 확인 {}/60<최대>'.format(REGISTERED_CONTAINER_KEYS[0], count))
  for container in client.containers.list():
    container_name = container.name
    if(container_name.lower().count(REGISTERED_CONTAINER_KEYS[0].strip()) > 0):
      print ('첫번째 컨테이너가 존재하고 시작됨을 감지하였으니 본 로직으로 돌아갑니다.')
      time.sleep(1)
      print ('\n'*100)
      returnFlag = True
      break
  count += 1
  time.sleep(1)

for service in SERVICE_DICT.keys():
  print ("SERVICE {}의 MASTER, SLAVE, ROLLBACK를 시작합니다.".format(service))
  SERVICE_DICT[service].burnup_container()

print ("BURNUP!!! {}초 대기".format(BURNUP_TIME))
time.sleep(BURNUP_TIME)

while True:
  try:
    for container in client.containers.list():
      container_name = container.name
      container_id = container.id
      container_hash = container.attrs['Image']
      container_image = container.attrs['Config']['Image']

      print('ID: {} 컨테이너 이름 : {} IMAGE : {} HASH : {}'.format(container_id, container_name, container_image, container_hash))
      if container_name in REGISTERED_CONTAINER_KEYS:
        SERVICE_MASTER_NAME = REGISTERED_CONTAINER_DICT[container_name]
        SERVICE_DICT[SERVICE_MASTER_NAME].update_info(
            container_name, container_id, container_hash, container_image)
    # ! 컨테이너 업데이트 ( 재시작시 id 변경되기때문에 )
  except Exception as E:
    print ("CONTAINER UPDATE_INFO ERROR")
    print (E)
    pass
  try:
    
    HAVE_UPDATE = False
    for SERVICE_KEY in SERVICE_DICT.keys():
      # SERVICE_DICT[SERVICE_KEY].repeat_checker()
      thread = threading.Thread(target=SERVICE_DICT[SERVICE_KEY].repeat_checker())
      thread.start()
      thread.join()
      if (SERVICE_DICT[SERVICE_KEY].haveUpdate()):
        if DEBUG_MODE:
          print(SERVICE_DICT[SERVICE_KEY].name, "HAS UPDATE ##")
        HAVE_UPDATE = True
        SERVICE_DICT[SERVICE_KEY].finishUpdate()
    
    if(HAVE_UPDATE):
      with open('/app/docker-compose-origin.yml', 'rt') as F:
        composeData = F.read()
        for SERVICE_KEY in SERVICE_DICT.keys():
          if(SERVICE_DICT[SERVICE_KEY].DEFAULTDICT['TARGETCONTAINER'].strip() != ''):
            env = SERVICE_DICT[SERVICE_KEY].currentEnvironment
            for key in env.keys():
              composeData = composeData.replace('${' + key.strip() + '}', env[key])
        with open('/app/docker-compose.yml', 'wt') as FO:
          FO.write(composeData)
      print("*************** NGINX UPDATE!!! **********")
      os.system("docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build nginx")
      NGINX_UPDATE = False

  except KeyboardInterrupt:
    print ('EXIT!')
    exit_handler()
    os._exit(0)
  time.sleep(SLEEP_TIME)
