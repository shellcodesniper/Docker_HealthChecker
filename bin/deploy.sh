docker build . -t shellcodesniper/healthchecker:latest -t shellcodesniper/healthchecker:test
docker push shellcodesniper/healthchecker

docker rmi -f $(docker images shellcodesniper/healthchecker -q)