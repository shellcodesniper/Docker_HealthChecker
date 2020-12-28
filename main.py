import parser
import docker
import os
import time
import service_manager

RUN_IN_DOCKER = os.environ.get('RUN_IN_DOCKER', False)

if (not os.path.isfile('/app/docker-compose.yml')):
  print('docker-compose.yml 파일을 /app/ 에 마운트 해주셔야 합니다.')
  os._exit(0)

config = parser.CONFIGURE
USE_CUSTOM_DOCKER = bool(str(config["기본"]["도커모드"]).lower().count('yes') > 0)
MANAUL_AUTH = bool(str(config["기본"]["도커허브로그인정보제공"]).lower().count('yes') > 0)
SLEEP_TIME = int(config['기본']['확인주기'])

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
  print(client.login(USERNAME, PASSWORD))
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
        level=SERVICE_LEVEL, container_name=SERVICE_CONTAINER_NAME)
    REGISTERED_CONTAINER_DICT[SERVICE_CONTAINER_NAME] = SERVICE_MASTER_NAME
  else:
    SERVICE_NAME_LIST.append(SERVICE_MASTER_NAME)
    SERVICE_DICT[SERVICE_MASTER_NAME] = service_manager.Service(name=SERVICE_MASTER_NAME)

  print ("서비스가 이미 실행중 혹은 컨테이너에 존재하는경우, 죽이고 삭제 진행. 컨테이너 이름 : [{}]".format(SERVICE_CONTAINER_NAME))
  try:
    os.system("docker kill {}".format(SERVICE_CONTAINER_NAME))
    os.system("docker rm {}".format(SERVICE_CONTAINER_NAME))
  except:
    pass

print(os.system('docker-compose -f /app/docker-compose.yml up'))

print ('Docker-compose Warm-up, Waiting 5s')
time.sleep(5)

REGISTERED_CONTAINER_KEYS = list(REGISTERED_CONTAINER_DICT.keys())
for container in client.containers.list():
  container_name = container.name
  container_id = container.id
  container_hash = container.attrs['Image']
  container_image = container.attrs['Config']['Image']

  print('ID: {} 컨테이너 이름 : {} IMAGE : {} HASH : {}'.format(
      container_id, container_name, container_image, container_hash))
  if container_name in REGISTERED_CONTAINER_KEYS:
    SERVICE_MASTER_NAME = REGISTERED_CONTAINER_DICT[container_name]
    SERVICE_DICT[SERVICE_MASTER_NAME].update_info(container_name, container_id, container_hash, container_image)

lat = client.images.pull("ilsamhz/multi_mall_back:latest")

while True:
  time.sleep(SLEEP_TIME)
  print (SERVICE_DICT)

# container.attrs['Image']

print(lat.id)
