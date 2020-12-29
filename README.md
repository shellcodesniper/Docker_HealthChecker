# DOCKER ZERO DOWNTIME DEPLOYMENT
`by KUUWANGE - admin@kuuwang.com`

Docker MASTER / SLAVE / ROLLBACK MANAGER

nginx + docker 이미지를 이용하여 쉬운 무중단 배포환경설정을 구성하기위한 프로젝트입니다. 내부 프로젝트는 파이썬으로 되어있습니다.

run.sh ( 실행 스크립트 예시)
```bash
docker pull shellcodesniper/healthchecker:stable;
docker kill test;
docker rm multitool;
docker run --name multitool \
	-e DEBUG_MODE=yes \
	-e CHECK_POOL=no \
	-v $(pwd)/config.ini:/app/config.ini \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v $(pwd)/docker-compose.yml:/app/docker-compose-origin.yml \
	-v $(pwd)/etc/api.kuuwang.com/:/etc/ssl \
	-v $(pwd)/nginx:/app/nginx \
	shellcodesniper/healthchecker:stable
```

파일 목록
- config.ini ( 설정파일 - 없다면 빈파일을 만든후 도커 실행시에 자동 생성 )
- nginx/
  - nginx.conf ( NGINX 기본 설정파일 )
  - templates/
    - default.conf.template ( default.conf와 같은 역할, 환경변수 사용을 위해 template 으로 작성해둠)
- docker-compose.yml ( DOCKER COMPOSE 파일, config.ini 와 같이 세팅 진행시 정상 사용 가능 )

**중요**
빈 파일이라도 config.ini 파일을 생성한후 진행하여야 합니다.

NGINX 설정은 docker-compose 에서 폴더를 마운트 해줍니다.
nginx 폴더의
nginx.conf 는 기본 설정을
conf.d 아래에는 서비스별로 설정해주어야합니다.

