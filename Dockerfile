FROM python:3.9-slim

LABEL maintainer="wessenstam.at@gmail.com"

# Get the to be needed stuff in
RUN apt update && apt install -y curl && \
    pip3 install --upgrade pip && \
    pip3 install gspread && \
    pip3 install --upgrade oauth2client && \
    pip3 install numpy && \
    pip3 install pandas && \
    pip3 install flask && \
    pip3 install flask-wtf && \
    pip3 install gspread-formatting && \
    pip3 install gspread_formatting && \
    pip3 install pika && \
    pip3 install requests && \
    pip3 install natsort && \
    mkdir /json && \
    chmod 777 /json

WORKDIR /

ADD start.sh .

VOLUME /json

EXPOSE 5000

CMD ["sh", "start.sh"]