import time
import quick2wire.i2c as i2c
import re
import logging
from threading import Lock
from RPi import GPIO


# Support library for MCP23017 on Raspberry pi
# Currently following features are supported
# - Initialize Chip with address on i2c bus
# - Initialize Chip with Bank-Mode configured as on or off
# - Read from specific Register
# - Write to specific register
# - Setting a specific config in IOCON
# - Unsetting a specific config in IOCON
# - Initialize 

# - TODO: make PortManager compatible to Bank=0 mode 

# - TODO: implement 16 bit mode, affects:
# - read() method
# - write() method
# - interrupt mirrors setting(?)
#  
# there is no datasheet - althought the PFY claims to have one
# pinouts have been determined by checking the controller outputs
# it contains two HD44780 compatible controllers selected by E and E2 

# for a pinout and pinmap see the accompanying documentation directory

# usage
# shield = IOShield()
# display.send_text("Up up in the butt", 1, 2) # line, chip - this will display the text in the 3rd line

log = logging.getLogger("MCP23017")
BUS = i2c.I2CMaster()

GPIO.setmode(GPIO.BCM)

# Register Mapping for Bank SETTING mode
REGISTER_MAPPING = { 
  0 : {
    'IODIR': 0X00,
    'IPOL': 0X02,
    'GPINTEN': 0X04,
    'DEFVAL': 0X06,
    'INTCON': 0X08,
    'IOCON': 0X0A,
    'GPPU': 0X0C,
    'INTF': 0X0E,
    'INTCAP': 0X10,
    'GPIO': 0X12,
    'OLAT': 0X14
  },
 1: {
    'IODIR': 0X00,
    'IPOL': 0X01,
    'GPINTEN': 0X02,
    'DEFVAL': 0X03,
    'INTCON': 0X04,
    'IOCON': 0X05,
    'GPPU': 0X06,
    'INTF': 0X07,
    'INTCAP': 0X08,
    'GPIO': 0X09,
    'OLAT': 0X0A
  }
}


# mapping of bits inside icocon register
IOCON = {'BANK':0b10000000, 'MIRROR': 0b01000000, 'DISSLW': 0b00010000, 'HAEN': 0b00001000, 'ODR': 0b00000100, 'INTPOL': 0b00000010}

MODE_INPUT = 0
MODE_OUTPUT = 1

MODE_PULLUP_HIGH = 1
MODE_PULLUP_DISABLE = 0

MODE_INVERT = 1
MODE_NOINVERT = 0

class PortManager:

  state = 0b00000000
  external_callback = None
  parent = None
  PREFIX = None


  ## Valid prefix values:
  # bank = 0 : 0, 1
  # bank = 1 : 0x00, 0x10    
  def __init__(self, mcp, prefix, interrupt_pin, register_resolver = None):
    if register_resolver is not None:
      self._resolve_register = register_resolver
    log.debug("Initialize port 0x{0:x}".format(prefix))
    self.lock = Lock()
    self.PREFIX = prefix
    self.interrupt_pin = interrupt_pin
    self.parent = mcp
    log.debug("Initialize Pulldown for GPIO pin "+ str(self.interrupt_pin))
    GPIO.setup(self.interrupt_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


  def set_callback(self, callback):
    log.debug("Set callback "+str(callback))
    self.state = BUS.transaction(
      #Set port to input pin
      i2c.writing_bytes(self.parent.ADDRESS,self._resolve_register(self.parent.REGISTER['GPIO'])),
      i2c.reading(self.parent.ADDRESS, 1))[0][0] ^ 0b11111111
    log.debug("Re-Setting initial state of port is now 0b{0:b}".format(self.state))
    if self.external_callback is None:
      log.debug("first call of set_callback: enabling RPi interrupt")
      GPIO.add_event_detect(self.interrupt_pin, GPIO.RISING, callback = self.callback)
    self.external_callback = callback

  def callback(self, channel):
    log.info("Interrupt detected on address 0x{0:x} with prefix 0x{1:x}; channel {2}".format(self.parent.ADDRESS, self.PREFIX, channel))
    self.lock.acquire()
    log.debug("Lock aquired!")
    log.debug("Before State is 0b{0:b}".format(self.state))
    erg = BUS.transaction(
      #READ INTF TO FIND OUT INITIATING PIN
      i2c.writing_bytes(self.parent.ADDRESS,self._resolve_register(self.parent.REGISTER['INTF'])),
      i2c.reading(self.parent.ADDRESS,1),
      #READ INTCAP TO GET CURRENTLY ACTIVATED PINS | RESETS THE INTERRUPT
      i2c.writing_bytes(self.parent.ADDRESS,self._resolve_register(self.parent.REGISTER['INTCAP'])),
      i2c.reading(self.parent.ADDRESS,1),
      #READ GPIO TO GET CURRENTLY ACTIVATED PINS | RESETS THE INTERRUPT
      i2c.writing_bytes(self.parent.ADDRESS,self._resolve_register(self.parent.REGISTER['GPIO'])),
      i2c.reading(self.parent.ADDRESS,1),

    )

    intf = erg[0][0]
    log.debug("INTF was 0b{0:b}".format(intf))
    intcap = (erg[1][0] ^ 0b11111111)
    log.debug("INTCAP was 0b{0:b}".format(intcap))
    gpio = (erg[2][0] ^ 0b11111111)
    log.debug("GPIO was 0b{0:b}".format(gpio))

    current = intf | gpio
    
        
    #calculate only changes
    changes = (self.state ^ 0b11111111) & current

    #set new state
    self.state = gpio
    log.debug("After State is 0b{0:b}".format(self.state))

    self.lock.release()
    log.debug("Lock released!")

    #call callback after lock release
    log.debug("Sending changes 0b{0:b} to callback method".format(changes))
    self.external_callback(changes, self.PREFIX, self.parent.ADDRESS)

  ##########################
  #Arduino-Lib like methods
  ##########################

  def _resolve_register(self,register):
    if self.parent.BANK == 0:
      return self.PREFIX + register
    elif self.parent.BANK == 1:
      return self.PREFIX | register

  def _high_level_setter_single_pin(self, pin, mode, register):
    config = 1 << pin;
    if mode == 0:
      parent.unset_register(register, config)
    else:
      parent.set_register(register, config)

  #set single pin to specific mode
  def pin_mode(self, pin, mode):
    self._high_level_setter_single_pin(self, pin, mode, self._resolve_register(self.parent.REGISTER['IODIR']))
  #set all pins at once
  def pin_mode(self, mode):
    self.parent.write(self._resolve_register(self.parent.REGISTER['IODIR']), mode)
  
  #set single pullup  
  def pullup_mode(self, pin, mode):
    self._high_level_setter_single_pin(self, pin, mode, self._resolve_register(self.parent.REGISTER['GPPU']))
  #set all pullups at once
  def pullup_mode(self, mode):
    self.parent.write(self._resolve_register(self.parent.REGISTER['GPPU']), mode)


  #set single input invert  
  def input_invert(self, pin, mode):
    self._high_level_setter_single_pin(self, pin, mode, self._resolve_register(self.parent.REGISTER['IPOL']))
  #set all invertings 
  def input_invert(self, mode):
    self.parent.write(self._resolve_register(self.parent.REGISTER['IPOL']), mode)

  ####################
  # Interrupts
  ####################

  #set interrupt for single pin  
  def interrupt_enable(self, pin, mode):
    self._high_level_setter_single_pin(self, pin, mode, self._resolve_register(self.parent.REGISTER['GPINTEN']))
  #set inerrupt for all pins
  def interrupt_enable(self, mode):
    self.parent.write(self._resolve_register(self.parent.REGISTER['GPINTEN']), mode)

  #set interrupt on comare for all pins - set DEFVAL accordingly
  def interrupt_compare(self, mode):
    self.parent.write(self._resolve_register(self.parent.REGISTER['INTCON']), mode)

  #set interrupt on comare for all pins - set DEFVAL accordingly
  def interrupt_compare_value(self, mode):
    self.parent.write(self._resolve_register(self.parent.REGISTER['DEFVAL']), mode)

  ######################
  # Reading and Writing
  ######################

  #write single pin value
  def digital_write(self, pin, mode):
    self._high_level_setter_single_pin(self, pin, mode, self._resolve_register(self.parent.REGISTER['OLAT']))
  #write all pins
  def digital_write(self, mode):
    self.parent.write(self._resolve_register(self.parent.REGISTER['OLAT']), mode)

  #read single pin value
  def digital_read(self, pin):
    value = self.parent.read(self._resolve_register(self.parent.REGISTER['GPIO']))
    return (value >> pin) & 0b00000001
  #read all pins
  def digital_read(self):
    return self.parent.read(self._resolve_register(self.parent.REGISTER['GPIO']))




#################################
#
# Class modeling a MCP23017 chip
#
#################################




class MCP23017(object):
  ADDRESS = None
  BANK = None

  @property
  def REGISTER(self):
    return REGISTER_MAPPING[self.BANK]

  def __init__(self, address, bank = 0):
    log.info("Initialize MCP23017 on 0x{0:x}".format(address))
    #self._lock = Lock()
    self.ADDRESS = address
    self.BANK = bank
    #Set bank state for easier Addressing of banks (IOCON register)
    #EVERYTHING else goes to zero - some magic to write bit on both settings
    if self.BANK == 1: #assume has been bank=0 before
      BUS.transaction( 
        i2c.writing_bytes(self.ADDRESS,0x15, IOCON['BANK']),
        i2c.writing_bytes(self.ADDRESS,0x0A, IOCON['BANK']))
    elif self.BANK == 0:
      BUS.transaction( 
        i2c.writing_bytes(self.ADDRESS,0x15, 0 ),
        i2c.writing_bytes(self.ADDRESS,0x0A, 0 ))

  ################
  # Port generation
  # this essentially generates ports depending on your 
  # - bank config 
  # - given parameters
  ######################

  def generate_ports(self, interrupt_s):
    if isinstance(interrupt_s, dict): # 8-bit mode configuration
      ports = {}
      ports[str(self.ADDRESS)+'_A'] = PortManager(self, 0, interrupt_s['A'])
      ports[str(self.ADDRESS)+'_B'] = PortManager(self, 0x10 if self.BANK else 1, interrupt_s['B'])
      return ports
    elif isinstance(x, basestring): # 16-bit configuration - NOT SUPPORTED
        return None


  # to comfortably set and unset chip config
  def set_config(self, config):
      log.info("Access IOCON, adding: 0b{0:b}".format(config))
      self.set_register(self.REGISTER['IOCON'],config)

  def unset_config(self, config):
      log.info("Access IOCON, removing: 0b{0:b}".format(config))
      self.unset_register(self.REGISTER['IOCON'],config)

  # Support bitwise setting and unsetting of register values
  def set_register(self, register, config):
      log.debug("Register 0x{0:x} adding: 0b{1:b}".format(register, config))
      register_value = BUS.transaction(
              i2c.writing_bytes(self.ADDRESS, register),
              i2c.reading(self.ADDRESS, 1))
      log.debug("Register before 0b{0:b}".format(register_value[0][0]))
      BUS.transaction(
              i2c.writing_bytes(self.ADDRESS, register, register_value[0][0] | config))
      log.debug("Register after 0b{0:b}".format(register_value[0][0] | config))

  def unset_register(self, register, config):
      log.debug("Register 0x{0:x}, removing: 0b{1:b}".format(register, config))
      register_value = BUS.transaction(
              i2c.writing_bytes(self.ADDRESS, register),
              i2c.reading(self.ADDRESS, 1))
      log.debug("Register before 0b{0:b}".format(register_value[0][0]))
      BUS.transaction(
              i2c.writing_bytes(self.ADDRESS, register, register_value[0][0] & ~ config))
      log.debug("Register after 0b{0:b}".format(register_value[0][0] & (config ^ 0b11111111)))

  # read and write to specific register
  def read(self, register):
    byte = BUS.transaction(
              i2c.writing_bytes(self.ADDRESS, register),
              i2c.reading(self.ADDRESS, 1))
    log.debug("Reading from address 0x{0:x} register 0x{1:x} value 0b{2:b}".format(self.ADDRESS, register, byte[0][0]))
    return byte[0][0]
  
  def write(self, register, value):
    log.debug("Writing to address 0x{0:x} register 0x{1:x} value 0b{2:b}".format(self.ADDRESS, register, value))
    BUS.transaction(
      i2c.writing_bytes(self.ADDRESS, register ,value),
    )
