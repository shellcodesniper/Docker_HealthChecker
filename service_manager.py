import os
class Service():
  def __init__(self, name=''):
    self.name = name
    self.master = { "id":None, "hash": None, "image": None, "healthy": None }
    self.slave = {"id": None, "hash": None, "image": None, "healthy": None}
    self.rollback = {"id": None, "hash": None, "image": None, "healthy": None}
    self.registeredDict = {}
  
  def register_container(self, level='none', container_name='none'):
    level = level.lower()
    if(level.count('master') > 0):
      print("서비스이름 <{}> 에 MASTER LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.master = container_name
      self.registeredDict[container_name] = "master"
    elif(level.count('slave') > 0):
      print("서비스이름 <{}> 에 SLAVE LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.slave = container_name
      self.registeredDict[container_name] = "slave"
    elif(level.count('rollback') > 0):
      print("서비스이름 <{}> 에 ROLLBACK LEVEL 컨테이너 등록 [{}]".format(
          self.name, container_name))
      self.rollback = container_name
      self.registeredDict[container_name] = "rollback"
    else:
      print('오류입니다. 컨테이너 level은 master, slave, rollback 중 하나여야만 합니다. config.ini 파일을 확인하여주세요.')
      os._exit(0)

  def get_target_from_container_name(self, container_name):
    if(container_name in list(self.registeredDict.keys())):
      return self.registeredDict[container_name]
    else:
      return None

  def update_info(self, container_name, container_id, container_hash, container_image):
    level = self.get_target_from_container_name(container_name)
    if(level is not None):
      if (level == "master"):
        self.master['id'] = container_id
        self.master['hash'] = container_hash
        self.master['image'] = container_image
      elif (level == "slave"):
        self.slave['id'] = container_id
        self.slave['hash'] = container_hash
        self.slave['image'] = container_image
      elif (level == "rollback"):
        self.rollback['id'] = container_id
        self.rollback['hash'] = container_hash
        self.rollback['image'] = container_image
      else:
        print("update_info 오류입니다. 확인해보세요.")
