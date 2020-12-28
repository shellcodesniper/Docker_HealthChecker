import configparser
import os

CONFIGURE = configparser.ConfigParser()
if (os.path.isfile('config.ini')):
  CONFIGURE.read('config.ini')
  configChecked = (CONFIGURE.has_section('기본') and CONFIGURE.has_section('컨테이너'))
  if configChecked:
    if ((CONFIGURE.has_option('기본', '도커모드') and str(CONFIGURE['기본']['도커모드']).lower().count('yes') > 0)):
      configChecked = configChecked and CONFIGURE.has_option('도커설정', '접속정보')
      if not configChecked:
        print ('기본-도커모드가 yes로 설정되어있을경우, 도커설정-접속정보가 제공되어야 합니다.')
        os._exit(0)
    if ((CONFIGURE.has_option('기본', '도커허브로그인정보제공') and str(CONFIGURE['기본']['도커허브로그인정보제공']).lower().count('yes') > 0)):
      configChecked = configChecked and (\
        CONFIGURE.has_option('도커허브', '아이디')\
        and CONFIGURE.has_option('도커허브', '비밀번호')\
        and str(CONFIGURE['도커허브']['아이디']).lower().strip() != 'none'
        and str(CONFIGURE['도커허브']['비밀번호']).lower().strip() != 'none')
      # ! 도커 허브 아이디 / 비밀번호 제공 확인
      if not configChecked:
        print ('도커허브 로그인 정보 제공에 동의하였지만 도커 허브 로그인 정보가 제공되지 않았습니다.')
        os._exit(0)
  else:
    print ('기본정보와 컨테이너 정보가 제공되지 않았습니다. config.ini를 삭제하고 재실행하여 설정해주시기 바랍니다.')
else:
  # ! 기본 설정 파일 만들기
  CONFIGURE['기본'] = {
      '확인주기': '30',
      '도커허브로그인정보제공': 'no',
      '도커모드': 'no',
  }
  CONFIGURE['도커설정'] = {
    '접속정보': 'unix://var/run/docker.sock',
  }
  CONFIGURE['도커허브'] = {
    '아이디': 'NONE',
    '비밀번호': 'NONE',
  }

  CONFIGURE['컨테이너'] = {
    '서비스이름_master': '컨테이너 이름1',
    '서비스이름_slave': '컨테이너 이름2',
    '서비스이름_rollback': '컨테이너 이름3',
  }
  CONFIGURE['작성방법 명시(작성금지)'] = {
    '도커모드란1': '도커에서 접속시에 var/run/docker.sock 등을 마운트 하여 사용할경우 도커설정-접속정보와 같이 설정',
    '도커모드란2': 'yes : 도커설정-접속정보 사용, no: 시스템에 환경 docker 접속정보 사용',
    '컨테이너 작성방법1': '기본컨테이너는 \'서비스이름_master\':\'컨테이너이름\'의 형태',
    '컨테이너 작성방법2': 'SLAVE 컨테이너는 \'서비스이름_slave\':\'컨테이너이름\'의 형태',
    '컨테이너 작성방법3': 'ROLLBACK 컨테이너는 \'서비스이름_rollback\':\'컨테이너이름\'의 형태',
    '컨테이너 작성방법4': '컨테이너 항목은 master,slave,rollback 이렇게 세가지 항목이 들어간다면 몇가지 서비스든 작성 가능합니다.',
    '컨테이너 작성방법5': '컨테이너 항목은 {서비스 이름}_{목적}:{컨테이너이름} 으로 계속 작성 가능합니다.',
    '이미지 업데이트 절차': '컨테이너 항목에 정의된 컨테이너 이름들이 실행중인 이미지를 최신으로 가져옵니다.',
  }

  with open('config.ini', 'w') as configFile:
    CONFIGURE.write(configFile)
  print ('###############################################\n'*100)
  print('config.ini 파일을 작성하여야 합니다. ini파일 형식을 따라갑니다. :(다중라인) =(한줄 입력)\n'*20)
  os._exit(0)

