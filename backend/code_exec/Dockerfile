FROM python:3.12-slim

# Install compilers and Java
RUN apt-get update && apt-get install -y \
    gcc g++ default-jdk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /sandbox

# Non-root user for extra safety
RUN useradd -m runner
USER runner

CMD ["bash"]
