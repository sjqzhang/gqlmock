FROM golang:1.16
RUN apt update && apt install python3-pip -y && pip3 install flask requests ops_channel -U
WORKDIR /app/gqlmock
RUN cd /app && git clone https://github.com/99designs/gqlgen.git && cd gqlgen && git checkout v0.17.2 && go build -o gqlgen main.go && mv gqlgen /usr/local/bin/gqlgen

COPY ./ /app/gqlmock

RUN cp /app/gqlmock/cli /bin/cli && chmod +x /bin/cli && ln /usr/bin/python3 /usr/bin/python


ENTRYPOINT ["python", "app.py"]