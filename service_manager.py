import os
import docker
import copy
import time
import io
import logger
import parser
import threading
import requests
import logging

config = parser.CONFIGURE

SERVER_ID = str(config["기본"]["SERVER_ID"].strip())
if(SERVER_ID == "" or SERVER_ID == "USE_IP"):
  SERVER_ID = requests.get('https://api.kuuwang.com/ip').text

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

if (IS_LOGGING):
  BUCKET = str(config["LOGGING"]["BUCKET"].strip())
  LOG_ROOT = str(config["LOGGING"]["ROOT_PATH"].strip())
  ACCESS_KEY = str(config["LOGGING"]["ACCESS_KEY"].strip())
  SECRET_KEY = str(config["LOGGING"]["SECRET_KEY"].strip())
  REGION_NAME = str(config["LOGGING"]["REGION_NAME"].strip())
  HEALTHCHECKER_LOGNAME = str(
      config["LOGGING"]["HEALTHCHECKER_LOGNAME"].strip())
  MAX_FILE_SIZE_BYTES = int(
      config["LOGGING"]["MAX_FILE_SIZE_MB"].strip()) * (1024 ** 2)
  TIME_ROTATION = int(config["LOGGING"]["TIME_ROTATION"].strip())


DEBUG_MODE = bool(str(os.environ.get('DEBUG_MODE', 'no')).lower().count('yes') > 0)
VERBOSE_MODE = (str(os.environ.get('VERBOSE_MODE', 'no')).lower().count('yes') > 0)

USE_CRON = False
try:
  USE_CRON = bool(str(config["기본"]["USE_CRON"]).lower().count('yes') > 0)
except Exception as E:
  print('NO CRON')
  print(E)
  pass

container_dict = { "id":"", "name": "", 'service_name': "", "hash": "", "last_hash":"", "image": "", "isRun": False, "healthy": True, "log": "", "fail": False, "logPath": ''}
class Service():
  def __init__(self, name='', client=docker.DockerClient, ENVDICT={}, DEFAULTDICT={}, checkInterval=2, currentContainer='', isLogging=False, logger=None):
    self.name = name
    self.client = client
    self.master = copy.deepcopy(container_dict)
    self.slave = copy.deepcopy(container_dict)
    self.rollback = copy.deepcopy(container_dict)
    self.ENVDICT = ENVDICT
    self.DEFAULTDICT = DEFAULTDICT
    self.registeredDict = {}
    self.IS_LOGGING = isLogging
    self.MAIN_LOGGER = logger

    self.updateCheckInterval = checkInterval
    self.updateCheckCounter = self.updateCheckInterval

    self.currentEnvironment= {
      self.ENVDICT["TARGETCONTAINER"]: self.DEFAULTDICT["TARGETCONTAINER"],
      self.ENVDICT["TARGETPORT"]: self.DEFAULTDICT["TARGETPORT"],
      self.ENVDICT["LISTENPORT"]: self.DEFAULTDICT["LISTENPORT"],
    }

    self.CURRENT_CONTAINER_NAME = currentContainer

    self.isUpdated = False

    self.print (self.ENVDICT, self.DEFAULTDICT)
  
  def print(self, *args, **kwargs):
    global IS_LOGGING, DEBUG_MODE, VERBOSE_MODE
    if IS_LOGGING:
      with io.StringIO() as F:
        print(" ".join(map(str, args)), file=F)
        output = F.getvalue()
        mode = kwargs.get('mode', 'debug')
        if(mode == 'debug'):
          self.MAIN_LOGGER.debug(output)
        elif(mode == 'info'):
          self.MAIN_LOGGER.info(output)
        elif(mode == 'error'):
          self.MAIN_LOGGER.error(output)
    if VERBOSE_MODE:
      print(" ".join(map(str, args)))
  
  def register_container(self, level='none', container_name='none', service_name='none'):
    global ACCESS_KEY, FORMATTER, SECRET_KEY, REGION_NAME, BUCKET, LOG_ROOT, SERVER_ID, IS_LOGGING
    level = level.lower()
    if(level.count('master') > 0):
      if DEBUG_MODE:
        self.print("서비스이름 <{}> 에 MASTER LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.registeredDict[container_name] = "master"
      self.master['service_name'] = service_name
      if (IS_LOGGING):
        self.master['logger'] = logger.create_logger("{}_{}".format(self.name, level), FORMATTER, ACCESS_KEY, SECRET_KEY, REGION_NAME, bucket=BUCKET, log_name='{}_log'.format(level),
                                                     log_root=LOG_ROOT, server_id=SERVER_ID, service_name=os.path.join(self.name, level), max_file_size_bytes=MAX_FILE_SIZE_BYTES, time_rotation=TIME_ROTATION)
    elif(level.count('slave') > 0):
      if DEBUG_MODE:
        self.print("서비스이름 <{}> 에 SLAVE LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.registeredDict[container_name] = "slave"
      self.slave['service_name'] = service_name
      if (IS_LOGGING):
        self.slave['logger'] = logger.create_logger("{}_{}".format(self.name, level), FORMATTER, ACCESS_KEY, SECRET_KEY, REGION_NAME, bucket=BUCKET, log_name='{}_log'.format(level),
                                                    log_root=LOG_ROOT, server_id=SERVER_ID, service_name=os.path.join(self.name, level), max_file_size_bytes=MAX_FILE_SIZE_BYTES, time_rotation=TIME_ROTATION)
    elif(level.count('rollback') > 0):
      if DEBUG_MODE:
        self.print("서비스이름 <{}> 에 ROLLBACK LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.registeredDict[container_name] = "rollback"
      self.rollback['service_name'] = service_name
      if (IS_LOGGING):
        self.rollback['logger'] = logger.create_logger("{}_{}".format(self.name, level), FORMATTER, ACCESS_KEY, SECRET_KEY, REGION_NAME, bucket=BUCKET, log_name='{}_log'.format(level),
                                                   log_root=LOG_ROOT, server_id=SERVER_ID, service_name=os.path.join(self.name, level), max_file_size_bytes=MAX_FILE_SIZE_BYTES, time_rotation=TIME_ROTATION)
    else:
      self.print('오류입니다. 컨테이너 level은 master, slave, rollback 중 하나여야만 합니다. config.ini 파일을 확인하여주세요.')
      os._exit(0)
  
  def burnup_container(self):
    # ! master, slave container를 깨웁니다.
    self.print('BURNUP MASTER')
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build {}'.format(self.master['service_name']))
    self.print('BURNUP SLAVE')
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build {}'.format(self.slave['service_name']))
    self.print('BURNUP ROLLBACK')
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build {}'.format(self.rollback['service_name']))

  def get_container_name_list(self):
    return list(set(self.registeredDict.keys()))

  def get_level_from_container_name(self, container_name):
    if(container_name in self.get_container_name_list()):
      return self.registeredDict[container_name]
    else:
      return None
  def get_container_from_container_name(self, container_name):
    if (container_name in self.get_container_name_list()):
      container = None
      if (self.get_level_from_container_name(container_name) == "master"):
        container = self.master
      elif (self.get_level_from_container_name(container_name) == "slave"):
        container = self.slave
      elif (self.get_level_from_container_name(container_name) == "rollback"):
        container = self.rollback
      return container
    else:
      return None
    
      
  def set_value(self, key, value, container_name='', level=''):
    if(level != ''):
      if (level == "master"):
        self.master[key] = value
      elif (level == "slave"):
        self.slave[key] = value
      elif (level == "rollback"):
        self.rollback[key] = value
    elif(container_name != ''):
        if (self.get_level_from_container_name(container_name) == "master"):
          self.master[key] = value
        elif (self.get_level_from_container_name(container_name) == "slave"):
          self.slave[key] = value
        elif (self.get_level_from_container_name(container_name) == "rollback"):
          self.rollback[key] = value
        else:
          self.print ("SET_VALUE 오류입니다.", key, value, container_name, level)

  def update_info(self, container_name, container_id, container_hash, container_image):
    level = self.get_level_from_container_name(container_name)
    # self.print ("LEVEL : {} CONTAINER : {}".format( level, container_name))
    if(level is not None):
      self.set_value('name', container_name, level=level)
      self.set_value('id', container_id, level=level)
      self.set_value('hash', container_hash, level=level)
      self.set_value('image', container_image, level=level)

  def repeat_checker(self, SERVICE_DICT):
    start_time = time.time()
    self.SERVICE_DICT = SERVICE_DICT

    self.update_health()
    try:
      self.get_log()
    except:
      pass
    self.check_health()

    if (DEBUG_MODE):
      self.print("REPEAT_CHECKER SPENT {}s".format(int(time.time()-start_time)))

  def update_checker(self, SERVICE_DICT):
    global USE_CRON
    start_time = time.time()
    self.SERVICE_DICT = SERVICE_DICT

    if(USE_CRON == False):
      self.updateCheckCounter -= 1
      if(self.updateCheckCounter <= 0):
        self.updateCheckCounter = self.updateCheckInterval
        self.check_update()
      self.print ("CHECK UPDATE : {}".format('검사 시작' if self.updateCheckCounter <= 0 else '{}회 이후'.format(self.updateCheckCounter)))
    else:
      self.print ('CHECK UPDATE CRON 바로 시작')
      self.check_update()
    if (DEBUG_MODE):
      self.print("UPDATE_CHECKER SPENT {}s".format(int(time.time()-start_time)))
    
  def get_log(self):
    logPath = self.master['logPath']
    # if(DEBUG_MODE):
      # print ('master LogPath', logPath)
    if(logPath != ''):
      with open(logPath, 'rt') as F:
        for row in F.readlines():
          self.master['logger'].debug(row)
      with open(logPath, 'wt') as F:
        F.write('')
    
    logPath = self.slave['logPath']
    if(logPath != ''):
      with open(logPath, 'rt') as F:
        for row in F.readlines():
          self.slave['logger'].debug(row)
      with open(logPath, 'wt') as F:
        F.write('')

    logPath = self.rollback['logPath']
    if(logPath != ''):
      with open(logPath, 'rt') as F:
        for row in F.readlines():
          self.rollback['logger'].debug(row)
      with open(logPath, 'wt') as F:
        F.write('')

  def update_health(self):
    for container_name in self.get_container_name_list():
      container = self.get_container_from_container_name(container_name)
      if(container is not None):
        self.print (container_name)
        try:
          c = self.client.containers.get(container['id'])
        except:
          self.set_value('isRun', False, container_name=container_name)
          self.set_value('healthy', 'dead', container_name=container_name)
          self.print ('update_health 컨테이너 죽은듯함. ( 넘기기 )')
          continue
        try:
          # if (DEBUG_MODE):
          #   self.print('\n' * 10)
          # self.print(c.attrs) # ! 컨테이너의 State 부분
          #   self.print ('\n'* 10)
          isRun = c.attrs['State'].get('Running', False)
          self.set_value('isRun', isRun, container_name=container_name)
          logPath = c.attrs.get('LogPath', '')
          self.set_value('logPath', logPath, container_name=container_name)
          healthy = (c.attrs['State']['Health']['Status'].strip())
          self.set_value('healthy', healthy, container_name=container_name)
          if healthy == 'unhealthy':
            try:
              ologs = c.attrs['State']['Health']['Log']
              logs = ""
              for log in ologs:
                logs += str(log["Output"]) + "\n"
              self.set_value('log', logs, container_name=container_name)
            except:
              self.print('output not defined')
        except Exception as E:
          self.print(E, mode='error')
          self.print ('No State Defined')
      else:
        self.print ('Container를 가져올수가 없습니다...')

  def check_health(self):
    for container_name in self.get_container_name_list():
      container = self.get_container_from_container_name(container_name)
      level = self.get_level_from_container_name(container_name)
      # self.print (container["name"], level, container['healthy'])
      if (container['healthy'] == 'unhealthy'):
        if DEBUG_MODE:
          self.print ("CONTAINER {}<{}> [{}] 가 HEALTHY 하지 않은이유.".format(container_name, level, container["fail"]))
          self.print (container["isRun"])
          self.print(container["log"].split('\'}')[0])
          self.print ("\n"*3)

        if (level == "master" and not self.master["fail"]):
          if DEBUG_MODE:
            self.print (level, self.master["fail"])
          self.change_nginx_env(self.slave)
          self.try_restart(self.master)
          self.master["fail"] = True
        
        if (level == "slave" and not self.slave["fail"]):
          self.slave["fail"] = True
          if(self.currentEnvironment[self.ENVDICT['TARGETCONTAINER']].strip().lower() != container_name.strip().lower()):
            self.try_restart(self.slave)
          else:
            if(self.master["fail"]):
              self.change_nginx_env(self.rollback)
              self.try_restart(self.master)
              self.try_restart(self.slave)
              try:
                reason = '[WARNING] 해당 서버 SLAVE와 MASTER CHECK가 FAIL로 알려졌습니다. ROLLBACK 으로 전환합니다.'
                requests.get('https://api.kuuwang.com/alert?token=mVWUJZqVn65BubaC&server_name={}&server_ip={}&reason={}'.format(SERVER_ID, requests.get('https://api.kuuwang.com/ip').text, reason))
                self.print('긴급! 관리자 메세지 발송')
              except:
                pass
              self.print ('긴급! 관리자 메세지 발송')
        
        if (level == "rollback" and not self.master["fail"] and self.slave["fail"]):
          self.try_restart(self.rollback)
        elif(level == "rollback" and (self.master["fail"] or self.slave["fail"])):
          if (self.master["fail"] and self.slave["fail"]):
            try:
              reason = '[SUPER ALERT] 해당 서버의 ROLLBACK/MASTER/SLAVE 전부 FAIL 입니다. 빠른 확인이 필요합니다.'
              requests.get('https://api.kuuwang.com/alert?token=mVWUJZqVn65BubaC&server_name={}&server_ip={}&reason={}'.format(SERVER_ID, requests.get('https://api.kuuwang.com/ip').text, reason))
              self.print('개긴급! 관리자 메세지 발송')
            except:
              pass
            self.print ('개긴급!')
          else:
            try:
              reason = '[ALERT] 해당 서버 ROLLBACK 은 죽었으나 MASTER/SLAVE 중 하나는 살아있습니다. 5분내에 정상화되지 않을경우 확인이 필요합니다.'
              requests.get('https://api.kuuwang.com/alert?token=mVWUJZqVn65BubaC&server_name={}&server_ip={}&reason={}'.format(
                  SERVER_ID, requests.get('https://api.kuuwang.com/ip').text, reason))
              self.print('좀긴급! 관리자 메세지 발송')
            except:
              pass
            self.print ('좀긴급!')
      else:
        if (level == "master"):
          if(self.currentEnvironment[self.ENVDICT['TARGETCONTAINER']] != self.master['name']):
            self.change_nginx_env(self.master)
          self.master["fail"] = False
        elif (level == "slave"):
          self.slave["fail"] = False
        elif (level == "rollback"):
          self.rollback["fail"] = False
          
  def force_update(self, container):
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --build {}'.format(container['name']))

  def change_nginx_env(self, container):
    self.print ('call change_nginx [{}]'.format(container['name']))
    SERVICE_DICT = self.SERVICE_DICT
    if(self.currentEnvironment[self.ENVDICT["TARGETCONTAINER"]].strip().lower() != container['name'].strip().lower()):
      self.currentEnvironment[self.ENVDICT['TARGETCONTAINER']] = container['name']
      self.currentEnvironment[self.ENVDICT['TARGETPORT']] = self.DEFAULTDICT['TARGETPORT']
      self.currentEnvironment[self.ENVDICT['LISTENPORT']] = self.DEFAULTDICT['LISTENPORT']

      with open('/app/docker-compose-origin.yml', 'rt') as F:
        composeData = F.read()
        for SERVICE_KEY in SERVICE_DICT.keys():
          if(SERVICE_DICT[SERVICE_KEY].DEFAULTDICT['TARGETCONTAINER'].strip() != ''):
            env = SERVICE_DICT[SERVICE_KEY].currentEnvironment
            for key in env.keys():
              composeData = composeData.replace('${' + key.strip() + '}', env[key])
        with open('/app/docker-compose.yml', 'wt') as FO:
          FO.write(composeData)
      self.print("*************** NGINX UPDATE!!! **********")
      self.print(os.system("docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build nginx"))
      # os.system("docker exec nginx nginx -s reload")

  def try_restart(self, container):
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build {}'.format(container['name']))
        
  
  def haveUpdate(self):
    return self.isUpdated

  def finishUpdate(self):
    self.isUpdated = False
  
  def _check_update(self, container):
    try:
      lat = self.client.images.get_registry_data(container['image'])
      if DEBUG_MODE:
        self.print(lat.id, container['last_hash'], container['image'])
      
      if(''.join(lat.id).strip() == ''.join(container['last_hash']).strip()):
        if DEBUG_MODE:
          self.print ("업데이트 없음..", container['name'])
        return False
      
      else:
        if DEBUG_MODE:
          self.print("업데이트 존재!", container['name'])
        container['new_hash'] = lat.id
        return True

    except Exception as E:
      self.print(E, mode='error')
      self.print("업데이트 가져오는도중에 에러발생 다음 update check에서 확인", mode='error')
      return False

  def check_update(self):
    update_Dict = {
      'master': False,
      'slave': False,
      'rollback': False,
    }
    for container_name in self.get_container_name_list():
      container = self.get_container_from_container_name(container_name)
      level = self.get_level_from_container_name(container_name)

      update_Dict[level.strip().lower()] = self._check_update(container)
    if DEBUG_MODE:
      self.print(update_Dict)
    if(update_Dict['rollback']):
      if DEBUG_MODE:
        self.print('master {} slave {}'.format(self.master['healthy'], self.slave['healthy']))
      if(self.master['healthy'] == 'healthy' or self.slave['healthy'] == 'healthy'):
        self.rollback['last_hash'] = self.rollback['new_hash']
        self.print(os.system('docker pull {}'.format(self.rollback['image'])))
        self.print(os.system('docker-compose -f /app/docker-compose.yml pull --no-parallel {}'.format(self.rollback['service_name'])))
        os.system('docker-compose -f /app/docker-compose.yml up -d --force-recreate --build --no-deps {}'.format(self.rollback['service_name']))
    
    if(update_Dict['master']):
      if DEBUG_MODE:
        self.print('master has update slave health:', self.slave['healthy'])
      if(self.slave['healthy'] == 'healthy'):
        self.master['last_hash'] = self.master['new_hash']
        self.change_nginx_env(self.slave)
        self.print(os.system('docker pull {}'.format(self.master['image'])))
        os.system('docker-compose -f /app/docker-compose.yml pull --no-parallel {}'.format(self.master['service_name']))
        os.system('docker-compose -f /app/docker-compose.yml up -d --force-recreate --build --no-deps {}'.format(self.master['service_name']))
      else:
        self.change_nginx_env(self.rollback)
        os.system('docker-compose -f /app/docker-compose.yml down --no-deps {} {}'.format(self.master['service_name'], self.slave['service_name']))
    
    if(update_Dict['slave']):
      if DEBUG_MODE:
        self.print('slave has update master health:', self.master['healthy'])
      if(self.master['healthy'] == 'healthy'):
        self.slave['last_hash'] = self.slave['new_hash']
        self.change_nginx_env(self.master)
        self.print(os.system('docker pull {}'.format(self.slave['image'])))
        os.system('docker-compose -f /app/docker-compose.yml pull --no-parallel {}'.format(self.slave['service_name']))
        os.system('docker-compose -f /app/docker-compose.yml up -d --force-recreate --build --no-deps {}'.format(self.slave['service_name']))
      else:
        self.change_nginx_env(self.rollback)
        os.system('docker-compose -f /app/docker-compose.yml down --no-deps {} {}'.format(self.master['service_name'], self.slave['service_name']))
    
