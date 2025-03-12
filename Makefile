default: build

config:
	$(eval DOCKER_COMPOSE = docker compose --project-name kaldi-server)

build: config 
	${DOCKER_COMPOSE} up -d --build	
	${DOCKER_COMPOSE} logs -f

down: config
	${DOCKER_COMPOSE} stop

clean: config down
	${DOCKER_COMPOSE} down --rmi all

purge: config down
	${DOCKER_COMPOSE} down --volumes --rmi all

