# Getting ubuntu image
FROM ubuntu:20.04

# Setting env variables
ENV DEBIAN_FRONTEND noninteractive
ENV user=user
ENV PATH="/home/${user}/.local/bin:${PATH}"
ENV ZEPHYR_BASE=/home/${user}/zephyrproject/zephyr
ENV APP=/home/${user}/workdir
ENV ZEPHYR_TOOLCHAIN_VARIANT=zephyr
ENV ZEPHYR_SDK_INSTALL_DIR=/home/${user}/.local/zephyr-sdk 
ENV USER_HOME=/home/${user}

# Creating directories
RUN mkdir -p ${ZEPHYR_BASE}
RUN mkdir -p ${APP}

# Installing packages
RUN dpkg --add-architecture i386 && \
	apt-get -y update && \
	apt-get -y upgrade && \
    apt-get -y install sudo


# Installing zephyr dependencias
## Installing default packages
RUN DEBIAN_FRONTEND="noninteractive" TZ="America/New_York" sudo apt-get install -y tzdata
RUN sudo apt-get install -y --no-install-recommends git ninja-build gperf \
	ccache dfu-util wget \
	python3-pip python3-setuptools python3-tk python3-wheel xz-utils file \
	make gcc gcc-multilib g++-multilib libsdl2-dev build-essential python3-dev cmake

## Changing workspace to tmp
RUN mkdir -p ${USER_HOME}/tmp
WORKDIR ${USER_HOME}/tmp

## Installing zephyr sdk
RUN wget -q "https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.12.0/zephyr-toolchain-arm-0.12.0-x86_64-linux-setup.run"
RUN sh "zephyr-toolchain-arm-0.12.0-x86_64-linux-setup.run" --quiet -- -d ${ZEPHYR_SDK_INSTALL_DIR} -y
RUN rm "zephyr-toolchain-arm-0.12.0-x86_64-linux-setup.run"

RUN wget -q "https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.12.0/zephyr-toolchain-x86_64-0.12.0-x86_64-linux-setup.run"
RUN sh "zephyr-toolchain-x86_64-0.12.0-x86_64-linux-setup.run" --quiet -- -d ${ZEPHYR_SDK_INSTALL_DIR} -y
RUN rm "zephyr-toolchain-x86_64-0.12.0-x86_64-linux-setup.run"

RUN wget -q "https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.12.0/zephyr-toolchain-riscv64-0.12.0-x86_64-linux-setup.run"
RUN sh "zephyr-toolchain-riscv64-0.12.0-x86_64-linux-setup.run" --quiet -- -d ${ZEPHYR_SDK_INSTALL_DIR} -y
RUN rm "zephyr-toolchain-riscv64-0.12.0-x86_64-linux-setup.run"

RUN sudo apt-get install -y --no-install-recommends policykit-1 libgtk2.0-0 screen uml-utilities gtk-sharp2 libc6-dev gcc python3 python3-pip libzmq5 mono-complete

RUN wget -q "https://github.com/renode/renode/releases/download/v1.12.0/renode_1.12.0_amd64.deb"
RUN sudo dpkg -i "renode_1.12.0_amd64.deb"
RUN rm "renode_1.12.0_amd64.deb"

# Getting zephyr and creating the environment 
#TODO: Ponto de falha por sempre utilizar o requirements do master. Isso foi feito pois em versões antigas do zephyr os requirements estavam quebrados.
# RUN git clone -q -b v2.3.0-rc1 --single-branch https://github.com/zephyrproject-rtos/zephyr ${ZEPHYR_BASE}
RUN git clone -q https://github.com/zephyrproject-rtos/zephyr --branch v2.4.0 --single-branch ${ZEPHYR_BASE}

RUN pip3 install wheel 
RUN pip3 install sh 
RUN pip3 install libscrc 
RUN pip3 install -r ${ZEPHYR_BASE}/scripts/requirements-base.txt 
RUN pip3 install --user -U west
RUN export PATH=~/.local/bin:$PATH

## Initializing west environment
RUN (cd ${ZEPHYR_BASE}/.. && west init -l ${ZEPHYR_BASE} && west update)

# Setting locales and language
RUN sudo apt-get install -y locales
RUN sudo locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Zeta IPC host dependencies 
RUN pip3 install pip install pyserial-asyncio
RUN pip3 install pyzmq

# Going to workdirectory
WORKDIR ${APP}
COPY zeta-tests /zeta-tests
COPY . .

CMD ["/zeta-tests"]
