# Qwen Chat Evaluation — 2026-03-26

This note captures live chat behavior observed after switching the local runtime from TinyLlama to Qwen2.5-1.5B-Instruct GGUF and after adding reply-source tracing (`assistant[rule]` vs `assistant[model]`).

## Runtime Context

- Model: `qwen2.5-1.5b-instruct-q4_k_m.gguf`
- Runtime: `llama.cpp` via `llama-cpp-python`
- Environment: WSL2 Ubuntu 24.04, CPU-only
- Chat retrieval mode: `fts`
- Rule/model tracing: enabled in chat output

## What Worked

- Exact fact capture and exact fact recall remained stable.
  - Example: favorite color `teal` was stored and recalled exactly.
- Open-ended reflective follow-up improved versus TinyLlama.
  - Qwen kept `teal` intact and produced a plausible personality-style answer.
- Multi-fact recall sometimes worked well when the model had enough context.
  - Example: `What is my dog's name and where do I live?` returned `Pixel` and `Bangalore`.
- General explanatory prompts improved.
  - Example: `Explain gravity.` returned a clean one-sentence answer.
- Entity recall through the model worked for some simple personal facts.
  - Example: laptop brand `Dell` was recalled correctly.

## What Did Not Work Well

### Rule-based acknowledgements still sound awkward in some cases

- `I have a dog named Pixel, I live in Bangalore, and I like Python programming.`
  - Reply: `Got it, Bharath. I'll remember that I have a dog named Pixel, I live in Bangalore, and I like Python programming.`
  - Problem: the response keeps the user's first-person wording and sounds mechanical.

### Multi-fact statements are not split into structured facts

- The system treated `I have a dog named Pixel, I live in Bangalore, and I like Python programming.` as one stored blob.
- This happened again for project-related facts and mixed preference statements.
- Consequence: recall depends on lexical overlap and prompt luck instead of typed memory.

### Corrections and updates are not being persisted deterministically

- `My favorite color is blue.` followed by `Actually, change it to black.`
  - The model acknowledged the correction.
  - Exact recall still returned `blue`.
- `My favorite language is Java.` followed by `I now prefer Python more than Java.`
  - The model acknowledged the new preference.
  - Exact recall still returned `Java`.
- This is the most important gap now that model quality has improved.

### Session directives are not separated from personal memory

- `Always respond in one sentence.` went to the model and received a poor answer.
- This should be classified as a chat/session preference or instruction, not as normal conversation or long-term memory.

### Compound recall remains too shallow in rule-based paths

- `My name is Bharath and I am building a robot with 4 wheels. Remember this for future conversations.`
  - Reply only covered the name.
- `Do you remember my name and what I'm building?`
  - Reply again only covered the name.
- The current exact-memory rule path is too slot-specific and loses the second fact.

### Number memory is not normalized

- `Remember this number: 4829317`
  - Reply: `Got it, Bharath. I'll remember that Remember this number: 4829317.`
- `What number did I ask you to remember?`
  - Reply: `I think this is what you mentioned: Remember this number: 4829317.`
- Numbers should be stored as a typed value, not as a raw sentence fragment.

### Some preference questions mix unrelated facts

- `What kind of food do I like?`
  - Reply included both `Python programming` and `dosa on weekends`.
- This shows the current retrieval/ranking path lacks fact typing and domain filtering.

### The model can still be too literal or too weak in creative tasks

- `Write a poem about space.`
  - Qwen refused instead of attempting a poem.
- This is not a memory bug, but it shows the model still needs prompt-quality evaluation for open-ended tasks.

### Multi-speaker text inside one message is not handled safely

- `User1: My name is Arun and I like chess.User2: My name is Priya and I like music.`
  - Rule path replied: `Your name is Bharath.`
- This input should either be rejected, ignored as unsafe for memory, or explicitly treated as quoted third-party content.

## Current Boundary That Still Makes Sense

Keep rules for:

- exact personal fact capture
- exact personal fact recall
- alias/name recall
- correction/update application once implemented deterministically

Let the model handle:

- general explanations
- reflective follow-ups
- creative tasks
- open-ended advice

The current problem is not that rules exist. The problem is that some rule-based paths are too texty and not structured enough.

## Improvement Plan

### 1. Add structured multi-fact extraction

- Split one user message into multiple typed memory facts.
- Example slots:
  - `favorite_color`
  - `favorite_fruit`
  - `preferred_language`
  - `pet_name`
  - `city`
  - `project_summary`
  - `platform`
  - `voice_requirement`
  - `remembered_number`

### 2. Add deterministic correction/update handling

- Detect update language such as:
  - `actually`
  - `change it to`
  - `now prefer`
  - `from now on`
- Apply updates to the existing slot instead of depending on the model acknowledgement.

### 3. Separate durable memory from session directives

- Distinguish:
  - personal facts
  - preferences
  - aliases
  - session instructions such as response style
- `Always respond in one sentence.` should not go into the same memory path as `My favorite fruit is mango.`

### 4. Improve rule-based acknowledgement templates

- Do not echo raw first-person multi-fact sentences.
- Convert stored facts into natural second-person confirmations.
- Example target style:
  - `Got it, Bharath. I'll remember that your dog's name is Pixel and you live in Bangalore.`

### 5. Add typed recall for compound questions

- Support exact multi-slot recall such as:
  - `What is my dog's name and where do I live?`
  - `Do you remember my name and what I'm building?`
- Build the answer from structured slots instead of relying on one ranked sentence.

### 6. Add transcript-based regression coverage

- Convert the strongest and weakest transcript examples from this session into tests.
- Include:
  - exact recall
  - correction handling
  - multi-fact storage
  - number memory
  - food preference filtering
  - directive vs memory separation
  - quoted/multi-speaker input rejection

### 7. Re-run rule boundary review after structured memory lands

- Once correction handling and typed facts exist, reassess which current rule paths are still necessary.
- Do not remove exact-memory guardrails before the structured path is proven stable.

## Recommendation

The next improvement should not be “remove rules.”

The next improvement should be “replace text-heavy rule paths with structured memory slots and typed answer assembly,” while continuing to use the model for open-ended responses.