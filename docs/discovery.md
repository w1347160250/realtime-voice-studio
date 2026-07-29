# Requirement Discovery

We will fill this file together.

## Product goal

- Build a realtime voice interaction tool for personal entertainment
- Main scenario: companion-style voice chat
- Product direction: balance latency and response quality instead of optimizing only one side

## Confirmed requirements

1. Primary user: solo use, for yourself
2. Main scenario: casual companion chat
3. Priority: balance between responsiveness and answer quality
4. Transcript: required
5. Login: required for v1, but temporary/simple auth is acceptable

## Still open

1. Do you want always-on open mic or push-to-talk first?
2. Should the AI reply with voice only, or voice plus on-screen text?
3. Do you want multiple personas, or only one assistant identity first?
4. Should chat history be saved locally first, or in a cloud database?
5. Do you want emotion or style controls such as gentle, playful, direct?

## First milestone candidate

The safest first milestone for this project is:

- browser-based voice chat demo
- live transcript panel
- AI replies in both text and speech
- simple temporary login
- session log with transcript storage

That is enough to validate whether the experience feels fun and natural before we invest in packaging or multi-platform work.

## Working recommendation

Start with web first, then consider desktop packaging later if one of these becomes important:

- background app behavior
- faster launch and app-like feel
- deeper device or operating system integration