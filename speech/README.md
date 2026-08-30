# Speech Module

The current production runtime keeps offline voice-command reception inside `main.py`.

`VoiceRecognitionThread` reads commands from the offline voice module through a serial port and places parsed commands into a thread-safe queue.

This folder is reserved for future extraction of the speech-recognition layer into an independent module.
