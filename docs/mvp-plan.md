# MVP Plan

## Product shape

Build a web app for personal realtime voice chat.

The first version should feel like a lightweight companion app:

- tap to start talking
- see your transcript as you speak
- hear the assistant speak back
- read the assistant text reply on screen
- sign in with a temporary/simple auth flow
- save transcript history per session

## Suggested v1 scope

1. Web client with microphone capture
2. Realtime or near-realtime speech-to-text
3. LLM response generation
4. Text-to-speech playback
5. Temporary login
6. Transcript history storage

## Suggested implementation order

1. Static UI shell
2. Temporary login flow
3. Transcript-only chat loop
4. Voice input
5. Voice output
6. Session history and persistence

## Azure resources likely needed

If you want to build on Azure, the practical minimum is:

1. Azure OpenAI for language and possibly speech-capable realtime features if your chosen model path uses it
2. Azure AI Speech for speech-to-text and text-to-speech if we separate speech services from the model layer
3. Azure App Service or Static Web Apps for hosting
4. A small database for accounts and transcripts, such as Azure Table Storage, Cosmos DB, or PostgreSQL

## What may be enough for the very first prototype

For the earliest prototype, you can delay some infrastructure by using:

1. local environment variables for credentials
2. simple temporary auth stored in app config or a lightweight local store
3. local file or sqlite transcript storage before moving to cloud storage

## Key decision

The main technical fork is this:

- simpler path: browser app plus backend API plus separate speech services
- richer path: realtime session architecture with streaming audio in both directions

The simpler path is safer for v1 unless natural interruption and ultra-low latency are the core value.