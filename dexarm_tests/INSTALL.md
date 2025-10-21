# DexArm Test Installation Guide

## Install Dependencies

```bash
cd D:\GitHub\ai-sketch-booth-claude
pip install -r requirements.txt
```

This will install:
- `Flask==3.0.0` - For the web server
- `pyserial>=3.5` - For DexArm serial communication

## What About pydexarm?

The official `pydexarm` library is not on PyPI. Instead, we've created a simple wrapper (`dexarm_tests/dexarm.py`) that uses `pyserial` directly to communicate with your DexArm.

Our wrapper supports all the basic commands you need:
- Connection and homing
- Move commands
- G-code sending
- Position queries

## Verify Installation

```bash
python -c "import serial; print('✅ pyserial installed')"
```

Should output: `✅ pyserial installed`

## Next Steps

Once installation is complete:

```bash
cd dexarm_tests
python 01_connection_test.py
```

If your DexArm is connected, it will auto-detect the port and test the connection!

## Troubleshooting

**ModuleNotFoundError: No module named 'serial'**
- Run: `pip install pyserial`

**Connection issues**
- Make sure DexArm is powered on
- Close Rotrics Studio if it's running
- Check USB cable connection
- Try manually specifying the port: `python 01_connection_test.py COM3`
