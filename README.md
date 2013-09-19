MCP23017-RPi-python
===================

Library for Raspberry interfacing with MCP23017 (e.g. on a shield)

Datasheet: http://ww1.microchip.com/downloads/en/devicedoc/21952b.pdf

Created with use of http://www.abelectronics.co.uk/products/3/Raspberry-Pi/18/IO-Pi-32-Channel-Port-Expander-for-the-Raspberry-Pi-computer-boards

MCP23017 can be used with bank=0 or bank=1 - what you prefer.

16-bit mode (2-byte write/read) is NOT SUPPORTED at the moment.
The focus is on a more generic interface which supports interrupts and (perhaps) the 8-bit MCP chips also.

Dependencies
============

quick2wire.i2c (http://quick2wire.com/)
RPi.GPIO (https://pypi.python.org/pypi/RPi.GPIO)

Features
========

MCP23017 class
--------------
MCP23017 class supports all low level configuration like accessing IOCON register, reading and writing any registers

- Initialize MCP23017 with address
- Optionally configure your Bank bit in constructor (default: BANK = 0)
- Read from specific Register
- Write to specific register
- Setting a specific Bit in IOCON
- Unsetting a specific Bit in IOCON

- Generating of two 8-bit-Port-Objects for a chip

Port Manager Class
------------------

Port manager supports more high level operations.

PortManager supplies the following methods to configure and work with an 8-bit-port (like Arduino lib on http://playground.arduino.cc/Main/MCP23S17 with more features)

*Set I/O mode*
`pin_mode`

*Set Pullups*
`pullup_mode`

*Set Input Invert*
`input_invert`

*Interrupt enabling*
`interrupt_enable`

*Set Inerrupt compare*
`interrupt_compare`

*Define Interrupt compare*
`interrupt_compare_value`

- Reading and writing
`digital_write`
`digital_read`

- Additionally it can handle a interrupt callback by passing a method:
`set_callback`

Usage
=====

Simple polling example

```python
from MCP23017 import MCP23017, PortManager, IOCON

#create chip with bank=1 mode on address 0x20
chip1 = MCP23017(0x20, 1)
#create chip with bank=0 mode on address 0x21
chip2 = MCP23017(0x21, 1)

#set some config bits on chip1
chip1.set_config(IOCON['INTPOL'])

#generate ports for chip1 - takes always a dict with keys 'A' and 'B' and the desired RPi GPIO interrupt pins
ports = chip1.generate_ports({'A':4, 'B':17})

#set ports of chip1 as input pins
for name,port in ports.items():
  print(" Setting up port "+name)
  #Set port to input pin
  port.pin_mode(0xff)

while True:
  for name,port in ports.items():
    print(" Reading port "+name)
    print(port.digital_read())

```

for setting up callbacks see also https://github.com/computerlyrik/PowerCounter



TODO
====
- TODO: implement 16 bit mode, affects:
 - read() method
 - write() method
 - interrupt mirrors setting(?) 
