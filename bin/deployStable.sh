docker build . -t shellcodesniper/healthchecker:stable
docker push shellcodesniper/healthchecker

docker rmi -f $(docker images shellcodesniper/healthchecker -q)