import configparser
import os

CONFIGURE = configparser.ConfigParser()
if (os.path.isfile('/app/config.ini') and os.stat('/app/config.ini').st_size > 2):
  CONFIGURE.read('/app/config.ini')
  configChecked = (CONFIGURE.has_section('기본') and CONFIGURE.has_section('컨테이너'))
  if configChecked:
    if ((CONFIGURE.has_option('기본', 'LOGGING') and str(CONFIGURE['기본']['LOGGING']).lower().count('yes') > 0)):
      if (CONFIGURE.has_section('LOGGING')):
        configChecked = configChecked \
          and CONFIGURE.has_option('LOGGING', 'BUCKET') \
          and CONFIGURE.has_option('LOGGING', 'ACCESS_KEY') \
          and CONFIGURE.has_option('LOGGING', 'SECRET_KEY') \
          and CONFIGURE.has_option('LOGGING', 'ROOT_PATH') \
          and CONFIGURE.has_option('LOGGING', 'REGION_NAME') \
          and CONFIGURE.has_option('LOGGING', 'HEALTHCHECKER_LOGNAME') \
          and CONFIGURE.has_option('LOGGING', 'TIME_ROTATION') \
          and CONFIGURE.has_option('LOGGING', 'MAX_FILE_SIZE_MB')
      else:
        print ('LOGGING 이 활성화되었을경우, LOGGING 섹션 정보가 제공되어야 합니다.')
        os._exit(0)
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
    '현재실행중인컨테이너이름': 'test',
    '확인주기': '30',
    'BURNUP대기시간': '20',
    '도커허브로그인정보제공': 'no',
    '도커모드': 'no',
    'NGINX사용': 'yes',
    '업데이트확인_주기': '5',
    'LOGGING': 'no',
    'SERVER_ID': 'USE_IP',
  }
  CONFIGURE['LOGGING'] = {
    'BUCKET': 'S3 BUCKET 이름',
    'ACCESS_KEY': '',
    'SECRET_KEY': '',
    'ROOT_PATH': 'logs',
    'REGION_NAME': 'ap-northeast-2',
    'HEALTHCHECKER_LOGNAME': 'healthchecker',
    'TIME_ROTATION': '3600',
    'MAX_FILE_SIZE_MB': '100',
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

  CONFIGURE['컨테이너_NGINX'] = {
    '서비스이름_TARGETPORT': 'template지정환경변수이름',
    '서비스이름_TARGETCONTAINER': 'template지정환경변수이름',
    '서비스이름_LISTENPORT': 'template지정환경변수이름',
  }

  CONFIGURE['컨테이너_기본설정'] = {
    '서비스이름_TARGETPORT': 'EXPOSE된 포트번호',
    '서비스이름_TARGETCONTAINER': '기본으로 시작될 컨테이너 이름',
    '서비스이름_LISTENPORT': 'NGINX에서 LISTEN 하고 있을 PORT 번호',
  }

  CONFIGURE['작성방법 명시(작성금지)'] = {
    'SERVER_ID': 'USE_IP 로 설정시에는 외부 ip를 서버 구분ID로 사용하게됩니다.',
    '업데이트확인_주기': '기본 - 업데이트확인_주기 : 확인주기 * 업데이트확인_주기 마다 업데이트를 확인합니다.',
    '현재실행중인컨테이너이름': '기본 - 현재실행중인컨테이너이름 : 현재 실행중인 도커 컨테이너의 이름',
    'NGINX사용': '기본 - NGINX사용 : 현재 비활성화 불가.',
    '도커모드란1': '도커에서 접속시에 var/run/docker.sock 등을 마운트 하여 사용할경우 도커설정-접속정보와 같이 설정',
    '도커모드란2': 'yes : 도커설정-접속정보 사용, no: 시스템에 환경 docker 접속정보 사용',
    '컨테이너 작성방법1': '기본컨테이너는 \'서비스이름_master\':\'컨테이너이름\'의 형태',
    '컨테이너 작성방법2': 'SLAVE 컨테이너는 \'서비스이름_slave\':\'컨테이너이름\'의 형태',
    '컨테이너 작성방법3': 'ROLLBACK 컨테이너는 \'서비스이름_rollback\':\'컨테이너이름\'의 형태',
    '컨테이너 작성방법4': '컨테이너 항목은 master,slave,rollback 이렇게 세가지 항목이 들어간다면 몇가지 서비스든 작성 가능합니다.',
    '컨테이너 작성방법5': '컨테이너 항목은 {서비스 이름}_{목적}:{컨테이너이름} 으로 계속 작성 가능합니다.',
    '컨테이너_NGINX 작성방법1': '서비스별로 서비스이름_TARGETPORT, 서비스이름_TARGETCONTAINER, 서비스이름_LISTENPORT 에 해당 서비스가 적용되는 template에 지정한 환경변수 이름을 적어주셔야 합니다.',
    '컨테이너_NGINX 작성방법2': 'template 파일들에 들어간 정보가 변환되어 적용됩니다.',
    '컨테이너_기본설정 작성방법1': '서비스별로 기본값들을 작성해주시면 됩니다.',
    '이미지 업데이트 절차': '컨테이너 항목에 정의된 컨테이너 이름들이 실행중인 이미지를 최신으로 가져옵니다.',
    'LOGGING 설정1': 'LOGGING은 S3에 업로드됩니다.',
    'LOGGING 설정2': 'LOGGING - ROOT_PATH 는 로그가 저장될 버킷내부 기준 폴더입니다.',
    'LOGGING 설정3': 'LOGGING TIME_ROTATION 은 초단위로 작성해주시면 됩니다.',
    'LOGGING 설정4': 'LOGGING MAX_FILE_SIZE_MB 는 로그파일당 최대크기이며 메가바이트단위로 작성해주시면됩니다.',
    'LOGGING 설정5': 'LOGGING BUCKET은 로그가 쌓일 버킷 이름이며, 이미 생성되어야 합니다.',
    'LOGGING 설정6': 'ACCESS_KEY, SECRET_KEY 는 발급받아주시고, S3관련 권한이 활성화되어야 합니다.',
    'LOGGING 설정7': 'REGION_NAME은 ap-northeast-2로 기본설정되어있으며, 한국으로 설정되어있습니다.',
    'LOGGING 설정8': 'HEALTHCHECKER_LOGNAME은 healthchecker의 로그가 저장될 서비스이름입니다.',
    'LOGGING 설정9': 'TIME_ROTATION은 초단위로 적어주시면 되고, 해당 시간단위로 로그파일이 새로고침됩니다.',
    'LOGGING 설정10': 'MAX_FILE_SIZE_MB는 MB단위로 작성해주시면되고, 해당 MB 단위로 로그파일이 새로고침됩니다.',
    'LOGGING 관련': '로그파일은 해당 버킷의 ROOT_PATH/SERVER_ID/SERVICE_NAME(서비스별로)/(master/slave/rollback).log로 저장됩니다.'
  }

  with open('/app/config.ini', 'w') as configFile:
    CONFIGURE.write(configFile)
  print ('###############################################\n'*100)
  print('config.ini 파일을 작성하여야 합니다. ini파일 형식을 따라갑니다. :(다중라인) =(한줄 입력)\n'*20)
  os._exit(0)

