FROM python:3.10.11-slim-bullseye
COPY --from=shinsenter/s6-overlay / /
COPY package_list_debian.txt /tmp/package_list_debian.txt
COPY requirements.txt /tmp/requirements.txt
ARG TZ=Asia/Shanghai
RUN set -xe && \
    export DEBIAN_FRONTEND="noninteractive" && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends wget bash ca-certificates && \
    # Debian can expose `netcat` as a virtual package, so resolve to a concrete provider.
    sed 's/^netcat$/netcat-openbsd/' /tmp/package_list_debian.txt > /tmp/package_list_debian.resolved.txt && \
    xargs -r apt-get install -y --no-install-recommends < /tmp/package_list_debian.resolved.txt && \
    ln -sf /command/with-contenv /usr/bin/with-contenv && \
    # zone time
    ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo "${TZ}" > /etc/timezone && \
    # locale
    locale-gen zh_CN.UTF-8 && \
    # chromedriver
    ln -sf /usr/bin/chromedriver /usr/lib/chromium/chromedriver && \
    # Python settings
    update-alternatives --install /usr/bin/python python /usr/local/bin/python3.10 3 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.10 3
RUN set -xe && \
    apt-get install -y --no-install-recommends build-essential unzip && \
    # Rclone
    curl https://rclone.org/install.sh | bash && \
    # Minio
    if [ "$(uname -m)" = "x86_64" ]; then ARCH=amd64; elif [ "$(uname -m)" = "aarch64" ]; then ARCH=arm64; else ARCH=amd64; fi && \
    curl -fsSL https://dl.min.io/client/mc/release/linux-${ARCH}/mc --create-dirs -o /usr/bin/mc && \
    chmod +x /usr/bin/mc && \
    # Pip requirements
    pip install --upgrade pip setuptools wheel && \
    pip install cython && \
    pip install -r /tmp/requirements.txt && \
    # Clear
    apt-get purge -y --auto-remove build-essential unzip && \
    apt-get clean -y && \
    rm -rf \
        /tmp/* \
        /root/.cache \
        /var/lib/apt/lists/* \
        /var/tmp/*
ENV S6_SERVICES_GRACETIME=30000 \
    S6_KILL_GRACETIME=60000 \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0 \
    S6_SYNC_DISKS=1 \
    HOME="/nt" \
    TERM="xterm" \
    PATH=${PATH}:/usr/lib/chromium:/command \
    TZ="Asia/Shanghai" \
    NASTOOL_CONFIG="/config/config.yaml" \
    NASTOOL_AUTO_UPDATE=false \
    NASTOOL_CN_UPDATE=true \
    NASTOOL_VERSION=master \
    REPO_URL="https://github.com/lljud/nas-tools.git" \
    PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple" \
    PUID=0 \
    PGID=0 \
    UMASK=000 \
    PYTHONWARNINGS="ignore:semaphore_tracker:UserWarning" \
    WORKDIR="/nas-tools"
WORKDIR ${WORKDIR}
RUN set -xe \
    && mkdir ${HOME} \
    && groupadd -r nt -g 911 \
    && useradd -r nt -g nt -d ${HOME} -s /bin/bash -u 911 \
    && python_ver=$(python3 -V | awk '{print $2}') \
    && echo "${WORKDIR}/" > /usr/local/lib/python${python_ver%.*}/site-packages/nas-tools.pth \
    && echo 'fs.inotify.max_user_watches=5242880' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=5242880' >> /etc/sysctl.conf \
    && echo "nt ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && git config --global pull.ff only \
    && git clone -b master ${REPO_URL} ${WORKDIR} --depth=1 --recurse-submodule \
    && git config --global --add safe.directory ${WORKDIR}
COPY --chmod=755 docker/rootfs /
EXPOSE 3000
VOLUME [ "/config" ]
ENTRYPOINT [ "/init" ]
