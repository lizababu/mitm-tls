NAME = mitm/https

.PHONY: build
build:
	docker build -t "$(NAME)" .
