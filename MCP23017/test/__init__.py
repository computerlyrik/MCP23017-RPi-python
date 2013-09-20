
def read(chip):
  for i in range(0x1B):
    byte = chip.read(i)

address = 0x20

print("BANK = 0, SEQOP = 0")
chip = MCP23017(address)
ports = chip.generate_ports({'A':4, 'B':17})
read(chip)

print("BANK = 1, SEQOP = 0")
chip = MCP23017(address)
ports = chip.generate_ports({'A':4, 'B':17})
read(chip)

print("BANK = 0, SEQOP = 1, MIRROR = 1")
chip = MCP23017(address) #does not matter
port = chip.generate_ports(4) #NO dict = 16 bit mode!
read(chip) # should show 16 bit words
port.digital_read()
