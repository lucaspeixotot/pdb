# Compiling and running this sample

There are some possibilities of running this sample. Initially we can run everything on the computer using only python models. After that we can run some models at the Renode instance. The last one is running some models at the board and the rest on the computer. For each of that we say technically the first one is Model in the Loop, the second is Software in the loop and the latest is Hardware in the loop. 

## Model in the loop

### Compiling
For this sample we only have Python code, so it won't be necessary to compile any code.

### Running 
We firstly run the zeta isc activity by running the following command:
```bash
zeta isc ./zeta.yaml /tmp/uart 115200
```
Note the arguments are:
 
 + Command: *zeta isc*
 + Middleware config file: *./zeta.yaml*
 + UART device: */tmp/uart* (this one is used by Renode, for actual device change to /dev/ttyUSB*)
 + UART baudrate: *115200*
 
 
Running the models: sunlight, core and light.

```bash
python3 sunlight_model.py
python3 core_model.py
python3 light_model.py

```

## Software in the loop

### Compiling
In this approach we are going to run some part of the code at the Renode environment and the other part at the computer. So we need to compile the code using some board supported by Renode. We choose *hifive1_revb* board based on stability. The compilation command must be:

```bash
west build -b hifive1_revb
```

### Running 
We firstly run the zeta isc activity by running the following command:
```bash
zeta isc ./zeta.yaml /tmp/uart 115200
renode renode_setup.resc
python3 light_model.py
```
Note the arguments are equals to the Model in the Loop example:
 
 + Command: *zeta isc*
 + Middleware config file: *./zeta.yaml*
 + UART device: */tmp/uart* (this one is used by Renode, for actual device change to /dev/ttyUSB*)
 + UART baudrate: *115200*
 
This command executes the Renode instance of the chosen board. 

```bash
renode renode_setup.resc
```
 
Running the models: sunlight and light.
```bash
python3 sunlight_model.py
python3 light_model.py
```

## Hardware in the loop

### Compiling
In this approach we are going to run some part of the code at the device (nRF52840) and the other part at the computer. So we need to compile the code to run in the board. The compilation command must be:

```bash
west build -b nrf52840dk_nrf52840
```

### Running 
We firstly run the zeta isc activity by running the following command:
```bash
zeta isc ./zeta.yaml /dev/ttyACM0 115200
```
Note the arguments are equals to the Model in the Loop example:
 
 + Command: *zeta isc*
 + Middleware config file: *./zeta.yaml*
 + UART device: */dev/ttyACM0* (this one the board uses to talk with the computer, for some devices this path would be */dev/ttyUSBX*)
 + UART baudrate: *115200*
 
This command flashes the code to the board attached to the USB. The board will run the core and one of light model.

```bash
west flash
```
 
Running a light model at the computer to compare the sync speed.
```bash
python3 light_model.py
```
