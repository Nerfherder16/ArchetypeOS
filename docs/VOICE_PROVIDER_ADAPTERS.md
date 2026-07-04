# Voice Provider Adapters

## Purpose

Voice features should not depend on one speech provider.

ArchetypeOS should support provider adapters for speech to text, text to speech, voice sessions, Claude, local LLMs, and future multimodal systems.

## Interfaces

```text
SpeechToTextProvider
TextToSpeechProvider
VoiceSessionProvider
LLMProvider
LocalLLMProvider
ClaudeProvider
```

## SpeechToTextProvider

Responsibilities:

- accept audio input
- transcribe speech
- return transcript
- return confidence
- optionally return timestamps and speaker labels

## TextToSpeechProvider

Responsibilities:

- accept text
- synthesize audio
- support streaming when possible
- return audio reference

## VoiceSessionProvider

Responsibilities:

- manage live session state
- track user identity
- track active project
- track driving mode
- route turns to the intent router

## Local Self Hosted Providers

The system should support self-hosted STT and TTS providers through local HTTP APIs or container networking.

Example environment variables:

```text
ARCHETYPE_STT_URL=http://stt:8000
ARCHETYPE_TTS_URL=http://tts:8001
ARCHETYPE_VOICE_DEFAULT_MODE=capture_only
```

## Provider Rules

- Do not hard-code providers.
- Keep provider abstraction stable.
- Log provider latency and errors.
- Support local-first operation.
- Allow cloud providers only when explicitly configured.

## Future Providers

- Whisper compatible STT
- Piper compatible TTS
- Coqui compatible TTS
- ElevenLabs
- OpenAI audio
- Anthropic/Claude text reasoning
- Ollama/local LLM
