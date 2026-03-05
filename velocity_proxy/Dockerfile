FROM eclipse-temurin:21-jre-alpine
RUN apk add --no-cache python3 py3-pip curl
WORKDIR /server
COPY requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt
CMD ["sh", "start.sh"]

