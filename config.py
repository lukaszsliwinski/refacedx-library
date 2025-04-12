# MIDI ports names
INPUT_PORT_NAME = 'reface DX 0'
OUTPUT_PORT_NAME = 'reface DX 1'

TIMEOUT = 5
DELAY = 0.2

# Dump request for reface DX (from documentation)
DUMP_REQUEST = [
    0x43,       # Yamaha ID
    0x20,       # Device Number
    0x7F,       # Group Number High
    0x1C,       # Group Number Low
    0x05,       # Model ID
    0x0E,       # Address High (VOICE Bulk Header)
    0x0F,       # Address Mid (VOICE Bulk Header)
    0x00        # Address Low (VOICE Bulk Header)
]