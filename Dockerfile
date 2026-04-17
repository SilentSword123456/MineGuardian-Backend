FROM python:3.12-slim

ARG TEMURIN_JRE_URL="https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.2%2B10/OpenJDK25U-jre_x64_linux_hotspot_25.0.2_10.tar.gz"

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    mkdir -p /opt/java/current && \
    curl -fsSL "$TEMURIN_JRE_URL" -o /tmp/temurin-jre.tar.gz && \
    tar -xzf /tmp/temurin-jre.tar.gz -C /opt/java/current --strip-components=1 && \
    rm -f /tmp/temurin-jre.tar.gz && \
    apt-get purge -y --auto-remove curl && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/opt/java/current
ENV PATH="${JAVA_HOME}/bin:${PATH}"

RUN java -version

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python", "main.py"]
