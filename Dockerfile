FROM alpine

LABEL maintainer="wessenstam.at@gmail.com"

# Get the to be needed stuff in
RUN apk add --no-cache python3 python3-dev py3-pip libstdc++ g++ git && \
    ln -s /usr/include/locale.h /usr/include/xlocale.h  && \
# Install the python dependencies
    pip3 install --upgrade pip && \
    pip3 install gspread && \
    pip3 install --upgrade oauth2client && \
    pip3 install numpy && \
    pip3 install pandas && \
    pip3 install flask && \
    pip3 install flask-wtf && \
    pip3 install gspread_formatting \
# Create the /json location where we put a volume so we can grab the credentials outside the container
    mkdir /json && \
    chmod 777 /json

WORKDIR /

ADD start.sh .

VOLUME /json

EXPOSE 5000

CMD ["sh", "start.sh"]
