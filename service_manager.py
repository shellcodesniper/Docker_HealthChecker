import os
import docker
import copy
import time

DEBUG_MODE = bool(str(os.environ.get('DEBUG_MODE', 'no')).lower().count('yes') > 0)

container_dict = { "id":"", "name": "", 'service_name': "", "hash": "", "image": "", "isRun": False, "healthy": True, "log": "", "fail": False}
class Service():
  def __init__(self, name='', client=docker.DockerClient, ENVDICT={}, DEFAULTDICT={}):
    self.name = name
    self.client = client
    self.master = copy.deepcopy(container_dict)
    self.slave = copy.deepcopy(container_dict)
    self.rollback = copy.deepcopy(container_dict)
    self.ENVDICT = ENVDICT
    self.DEFAULTDICT = DEFAULTDICT
    self.registeredDict = {}

    self.updateCheckInterval = 2
    self.updateCheckCounter = self.updateCheckInterval

    self.currentEnvironment= {
      self.ENVDICT["TARGETCONTAINER"]: self.DEFAULTDICT["TARGETCONTAINER"],
      self.ENVDICT["TARGETPORT"]: self.DEFAULTDICT["TARGETPORT"],
      self.ENVDICT["LISTENPORT"]: self.DEFAULTDICT["LISTENPORT"],
    }

    self.isUpdated = False

    print (self.ENVDICT, self.DEFAULTDICT)
  
  def register_container(self, level='none', container_name='none', service_name='none'):
    level = level.lower()
    if(level.count('master') > 0):
      if DEBUG_MODE:
        print("서비스이름 <{}> 에 MASTER LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.registeredDict[container_name] = "master"
      self.master['service_name'] = service_name
    elif(level.count('slave') > 0):
      if DEBUG_MODE:
        print("서비스이름 <{}> 에 SLAVE LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.registeredDict[container_name] = "slave"
      self.slave['service_name'] = service_name
    elif(level.count('rollback') > 0):
      if DEBUG_MODE:
        print("서비스이름 <{}> 에 ROLLBACK LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.registeredDict[container_name] = "rollback"
      self.rollback['service_name'] = service_name
    else:
      print('오류입니다. 컨테이너 level은 master, slave, rollback 중 하나여야만 합니다. config.ini 파일을 확인하여주세요.')
      os._exit(0)
  
  def burnup_container(self):
    # ! master, slave container를 깨웁니다.
    print('BURNUP MASTER')
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build {}'.format(self.master['service_name']))
    print('BURNUP SLAVE')
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --no-build {}'.format(self.slave['service_name']))
    print('BURNUP ROLLBACK')
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
          print ("SET_VALUE 오류입니다.", key, value, container_name, level)

  def update_info(self, container_name, container_id, container_hash, container_image):
    level = self.get_level_from_container_name(container_name)
    # print ("LEVEL : {} CONTAINER : {}".format( level, container_name))
    if(level is not None):
      self.set_value('name', container_name, level=level)
      self.set_value('id', container_id, level=level)
      self.set_value('hash', container_hash, level=level)
      self.set_value('image', container_image, level=level)

  def repeat_checker(self):
    self.update_health()
    self.check_health()
    
    self.updateCheckCounter -= 1

    print ("CHECK UPDATE : {}".format('검사 시작' if self.updateCheckCounter <= 0 else '{}회 이후'.format(self.updateCheckCounter)))

    if(self.updateCheckCounter <= 0):
      self.updateCheckCounter = self.updateCheckInterval
      self.check_update()


  def update_health(self):
    for container_name in self.get_container_name_list():
      container = self.get_container_from_container_name(container_name)
      if(container is not None):
        print (container_name)
        c = self.client.containers.get(container['id'])
        try:
          # print(c.attrs['State']) # ! 컨테이너의 State 부분
          isRun = c.attrs['State'].get('Running', False)
          self.set_value('isRun', isRun, container_name=container_name)
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
              print('output not defined')
        except Exception as E:
          print ('No State Defined')
      else:
        print ('Container를 가져올수가 없습니다...')

  def check_health(self):
    for container_name in self.get_container_name_list():
      container = self.get_container_from_container_name(container_name)
      level = self.get_level_from_container_name(container_name)
      # print (container["name"], level, container['healthy'])
      if (container['healthy'] == 'unhealthy'):
        if DEBUG_MODE:
          print ("CONTAINER {}<{}> [{}] 가 HEALTHY 하지 않은이유.".format(container_name, level, container["fail"]))
          print (container["isRun"])
          print(container["log"].split('\n')[0])

        # print ("\n"*3)
        if (level == "master" and not self.master["fail"]):
          if DEBUG_MODE:
            print (level, self.master["fail"])
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
              print ('긴급!')
        
        if (level == "rollback" and not self.master["fail"] and self.slave["fail"]):
          self.try_restart(self.rollback)
        elif(level == "rollback" and (self.master["fail"] or self.slave["fail"])):
          if (self.master["fail"] and self.slave["fail"]):
            print ('개긴급!')
          else:
            print ('좀긴급!')
      else:
        if (level == "master"):
          self.master["fail"] = False
        elif (level == "slave"):
          self.slave["fail"] = False
        elif (level == "rollback"):
          self.rollback["fail"] = False
    

        
        self.change_nginx_env(self.slave)
          
  def force_update(self, container):
    os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --build {}'.format(container['name']))

  def change_nginx_env(self, container):
    if(self.currentEnvironment[self.ENVDICT["TARGETCONTAINER"]].strip().lower() != container['name'].strip().lower()):
      self.currentEnvironment[self.ENVDICT['TARGETCONTAINER']] = container['name']
      self.currentEnvironment[self.ENVDICT['TARGETPORT']] = self.DEFAULTDICT['TARGETPORT']
      self.currentEnvironment[self.ENVDICT['LISTENPORT']] = self.DEFAULTDICT['LISTENPORT']
      self.isUpdated = True

  def try_restart(self, container):
    os.system('docker-compose -f /app/docker-compose.yml up -d --force-recreate --no-deps --no-build {}'.format(container['name']))
        
  
  def haveUpdate(self):
    return self.isUpdated

  def finishUpdate(self):
    self.isUpdated = False
  
  def _check_update(self, container):
    container['image']
    lat = self.client.images.pull(container['image'])
    print(lat.id, container['hash'])
    if(''.join(lat.id).strip() == ''.join(container['hash']).strip()):
      if DEBUG_MODE:
        print ("업데이트 없음..", container['name'])
      return False
    else:
      if DEBUG_MODE:
        print("업데이트 존재!", container['name'])
      return True

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
      print(update_Dict)
    if(update_Dict['rollback']):
      if(self.master['healthy'] == 'healthy' or self.master['healthy'] == 'healthy'):
        os.system('docker-compose -f /app/docker-compose.yml up --no-start --no-deps --build {}'.format(self.master['service_name']))
    
    if(update_Dict['master']):
      if DEBUG_MODE:
        print('master has update slave health:', self.slave['healthy'])
      if(self.slave['healthy'] == 'healthy'):
        self.change_nginx_env(self.slave)
        os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --build {}'.format(self.master['service_name']))
      else:
        self.change_nginx_env(self.rollback)
        os.system('docker-compose -f /app/docker-compose.yml down --no-deps {} {}'.format(self.master['service_name'], self.slave['service_name']))
    
    if(update_Dict['slave']):
      if DEBUG_MODE:
        print('slave has update master health:', self.master['healthy'])
      if(self.master['healthy'] == 'healthy'):
        self.change_nginx_env(self.master)
        os.system('docker-compose -f /app/docker-compose.yml up -d --no-deps --build {}'.format(self.slave['service_name']))
      else:
        self.change_nginx_env(self.rollback)
        os.system('docker-compose -f /app/docker-compose.yml down --no-deps {} {}'.format(self.master['service_name'], self.slave['service_name']))
    
