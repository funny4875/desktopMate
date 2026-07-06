# VRM interactive assistant spec

## Goal
Make `app.py` turn the displayed VRM character into a voice-interactive assistant.

## Functional requirements
- Load `promptInjection.txt` for every Gemini request.
- Include only the previous completed user/assistant exchange in the next request.
- Use the Gemini API setup pattern from `C:\Users\ky\Desktop\aiRoughGuy-main\AI流氓.py`: prompt for an API key if needed, list available models, persist the API key under the user's app data folder, and call `client.models.generate_content(...)`.
- Continuously listen to the microphone with `speech_recognition` and recognize Traditional Chinese (`zh-TW`).
- Use `pyttsx3` for spoken replies and prefer a female voice.
- Interpret the Gemini response format as:
  - First non-empty line: VRMA animation name.
  - Remaining lines: text to display and speak.
- Only accept these animation names: `Angry`, `Blush`, `Clapping`, `Goodbye`, `Jump`, `LookAround`, `Sad`, `Sleepy`, `Surprised`, `Thinking`.
- Do not show `Relax.vrma` in the right-click VRMA menu.
- Play `VRMA/<animation>.vrma` for the first-line animation.
- Display the response text in the VRM window while speaking it.
- Keep the existing VRM drag, pose cycling, right-click VRMA menu, and transparent window behavior.

## Error handling
- If Gemini setup fails or dependencies are missing, keep the VRM window usable and show a clear status message.
- If speech recognition times out or cannot understand audio, do not interrupt the character.
- If Gemini returns an invalid animation name, use `Thinking`.
- If Gemini returns no spoken text, use a short fallback message.
- Avoid overlapping AI requests; ignore new recognized speech while one reply is still being generated/spoken.

## Validation checklist
- `app.py` compiles with `python -m py_compile app.py`.
- `index.html` exposes a callable animation bridge for Python.
- `index.html` exposes a callable text display bridge for Python.
- Static checks confirm `promptInjection.txt`, previous-turn context, Gemini calls, speech recognition, TTS, and animation parsing exist in `app.py`.
- The app is not auto-launched during validation because it may activate the microphone and voice output.

## Validation results
- Passed: `python -m py_compile app.py`.
- Passed: dependency discovery found `PySide6`, `speech_recognition`, `pyttsx3`, `google.genai`, and `pyaudio`.
- Passed: static checks found `promptInjection.txt` loading, one-turn `previous_exchange`, Gemini `generate_content`, `speech_recognition` recognition, `pyttsx3` TTS, response parsing, `playVrmaByName`, and `showAssistantText`.
- Passed: response parser accepts valid animation names and falls back to `Thinking` for invalid or empty responses.
- Passed: `Relax` is removed from accepted animation names, `Relax.vrma` is filtered out of the right-click menu, and prompt guidance no longer asks Gemini to use `Relax`.
- Not auto-launched: app startup opens microphone listening and voice output, so validation stopped at compile/static/unit-level checks.
