# Troubleshooting

## Why does Ctrl+Alt+R report a conflict?

Windows permits only one owner for most global chord combinations. Choose another
shortcut in Settings or close/reconfigure the owning application. Speak Helper logs
the Windows error and keeps other successfully registered actions active.

## Why can selection capture fail in an administrator window?

Windows User Interface Privilege Isolation can block input injected from a normal
process into an elevated process. Run the target application and Speak Helper at the
same integrity level.

## Why was my previous clipboard content restored?

Read Selection is a transaction and restores the prior clipboard by default. Turn
off restoration under Clipboard if you want the selected text to remain copied.

## Can a local TTS server omit the API key?

Yes. Speak Helper omits the Authorization header when the key is empty. The server
must provide an OpenAI-compatible `/audio/speech` endpoint.

## Does Qwen3-TTS require CUDA in Speak Helper?

No. Run the model server in a separate environment. Speak Helper is only the HTTP
client and audio UI.

## Are clipboard contents written to logs?

No. Structured events record stage names and text lengths, never complete captured
or OCR text, API keys, or authorization headers.
