# WSL Development-Device Validation Runbook

Purpose
- Validate the current Windows-hosted development devices from WSL2/WSLg before buying Raspberry Pi-side audio and camera hardware.
- Keep this workflow explicitly development-only. Passing these checks does not imply production support on Raspberry Pi.

Current target devices
- Microphone: Blue Yeti
- Speaker: Windows-connected speaker reached from WSLg / Windows audio routing
- Camera: Android phone over USB, only if WSL can consume it directly or through an explicit bridge

Out of scope
- Raspberry Pi hardware setup
- Production TTS selection beyond the current pyttsx3 development path
- Real microphone or camera adapter implementation in the repo before the device path is proven

## Preflight

Run these checks before starting any validation so the work stays isolated from `main`:

```bash
git status --short --branch
git fetch origin --prune
git rev-list --left-right --count main...origin/main
git switch -c feature/wsl-dev-device-validation
```

Expected outcome
- Local `main` is compared to `origin/main` without rebasing, resetting, or deleting local artifacts.
- Validation work happens on a feature branch, not directly on `main`.

## Validation Order

1. Speaker output through the Windows-connected speaker
2. Blue Yeti microphone input from WSL
3. Android phone camera path from WSL
4. Documentation and tracker updates after the device checks complete

This order matches the bridge tasks in `docs/TASK_TRACKER.md` and the WSL notes in `docs/phase1/WSL_AUDIO_CAMERA.md`.

## 1. Speaker Validation

Goal
- Confirm that the existing development TTS path in `src/tts_adapter.py` produces audible output through the Windows-connected speaker from WSL.

Repo-grounded rationale
- `src/tts_adapter.py` already provides `Pyttsx3TTSAdapter`.
- `main.py` already supports `--tts` and defaults to mock model mode, so this path can be validated without any model runtime changes.

Bootstrap prerequisites
- `scripts/setup_wsl_dev.sh` should install `alsa-utils`, `pulseaudio-utils`, and `libasound2-plugins`.
- On WSLg, ALSA needs a default device mapped to PulseAudio. The bootstrap script now creates `~/.asoundrc` with:

```text
pcm.!default pulse
ctl.!default pulse
```

- If `~/.asoundrc` already exists, leave it in place and inspect it before overriding user-specific audio settings.

Commands

Direct adapter test:

```bash
source .venv/bin/activate
python -c "from src.tts_adapter import Pyttsx3TTSAdapter; Pyttsx3TTSAdapter().speak('WSL speaker validation complete')"
```

Integrated runtime test:

```bash
source .venv/bin/activate
printf 'stop\nexit\n' | python main.py --tts
```

Success criteria
- The direct adapter test speaks a short phrase audibly through the Windows-connected speaker.
- The integrated runtime test starts normally and produces an audible response for the injected command.
- The working command and any required environment detail are recorded.

Current validation note
- Validated on 2026-03-27 in WSLg with the Windows-connected speaker after installing `alsa-utils`, `pulseaudio-utils`, and `libasound2-plugins`, and routing ALSA default output to Pulse via `~/.asoundrc`.
- Speech output was audible from both the direct adapter test and `main.py --tts`, but the current pyttsx3/espeak-ng voice quality was rough. Treat this as a development-path pass, not a production voice-quality decision.
- In this WSLg setup, the effective speaker follows the Windows default or forwarded output device. If the Windows default speaker changes, WSL playback should follow that route without repo code changes, but device identity is not stable inside WSL.

Failure classification
- `pyttsx3` import or init failure: dependency/runtime issue in WSL.
- `sh: 1: aplay: not found`: the Linux playback utility is missing in WSL. Install `alsa-utils` or rerun `scripts/setup_wsl_dev.sh` after the bootstrap script includes it.
- `aplay: audio open error: No such file or directory` with PulseAudio available: ALSA has no default playback device. Install `pulseaudio-utils` and `libasound2-plugins`, then configure `~/.asoundrc` to route the default device to `pulse`.
- No audible output despite no exception: WSLg or Windows audio-routing problem.
- Runtime path works only in one of the two commands: document which path is approved for development.

## 2. Microphone Validation

Goal
- Confirm that WSL exposes the Blue Yeti to Linux-side tooling strongly enough to support future Vosk and `input_listener` work.

Repo-grounded rationale
- `requirements.txt` includes `sounddevice` and `vosk`.
- `src/audio_adapter.py` is still interface-only, so the immediate task is validating the device path, not implementing production STT.

Commands

Enumerate WSL audio devices:

```bash
source .venv/bin/activate
pactl info
pactl list short sources
arecord -L
python - <<'PY'
import sounddevice as sd
for index, device in enumerate(sd.query_devices()):
    print(index, device['name'], 'in=', device['max_input_channels'], 'out=', device['max_output_channels'])
PY
```

Short capture test:

```bash
source .venv/bin/activate
arecord -f cd -d 5 /tmp/blue-yeti-test.wav
ffprobe /tmp/blue-yeti-test.wav
```

Success criteria
- The Blue Yeti is visible in at least one Linux-side device listing from WSL.
- A short capture completes and produces a non-empty audio file.
- The validated capture path is reproducible enough to reuse later for Vosk and input-listener experiments.

Current validation note
- Validated on 2026-03-27 through the WSLg PulseAudio source exposed as `RDPSource`.
- `sounddevice` saw `pulse` and `default` devices, and `arecord -D pulse` produced a non-empty capture file with spoken-audio levels (`mean_volume: -26.7 dB`, `max_volume: -9.4 dB`).
- Treat this as a development-path pass. The Blue Yeti is not named explicitly inside WSL; the effective source depends on the Windows-side default or forwarded microphone input path.
- If the Windows default or forwarded microphone changes, the effective WSL microphone path should follow that routed source automatically. This validation is for default-device routing, not stable per-device binding inside WSL.

Failure classification
- Device visible in Windows only: not an approved WSL microphone path yet.
- `sounddevice` sees no input devices: WSL audio-input bridge issue.
- `arecord` or PulseAudio can enumerate but not capture: partial path, still blocked for development use.

Decision note
- Do not implement a real STT adapter until one repeatable Linux-side capture path is confirmed.

## 3. Android Camera Validation

Goal
- Determine whether the Android phone camera is actually usable from WSL, not merely visible to Windows.

Repo-grounded rationale
- `src/camera_adapter.py` is mock-only today.
- `docs/phase1/WSL_AUDIO_CAMERA.md` already treats Android-over-USB as a development convenience path that must be validated before relying on it.

Windows-side preparation

```powershell
usbipd wsl list
usbipd wsl attach --busid <busid>
```

Modern Windows 11 + usbipd-win (v5.x) flow

Use an elevated PowerShell session (Run as Administrator):

```powershell
# one-time install if needed
winget install --id dorssel.usbipd-win -e --accept-package-agreements --accept-source-agreements

# list USB devices and find the phone in webcam mode (example: BUSID 1-7 Android Webcam)
& 'C:\Program Files\usbipd-win\usbipd.exe' list

# bind is required once per device/port and requires admin
& 'C:\Program Files\usbipd-win\usbipd.exe' bind --busid <busid>

# attach to WSL (can be rerun after reconnects)
& 'C:\Program Files\usbipd-win\usbipd.exe' attach --wsl --busid <busid>
```

Notes
- `bind` requires administrator privileges.
- If `usbipd` is not on PATH yet, use the full executable path shown above.
- Re-run `list` after reconnecting the phone because BUSID can change.

WSL-side enumeration and probe:

```bash
ls -l /dev/video*
v4l2-ctl --list-devices
ffmpeg -f video4linux2 -i /dev/video0 -frames:v 1 /tmp/android-camera-test.jpg
file /tmp/android-camera-test.jpg
```

Success criteria
- WSL exposes a usable `/dev/video*` device or another explicit bridge endpoint.
- A minimal frame grab succeeds from WSL.
- The connection mode is specific and repeatable enough to document as an approved development path.

Current validation note
- As of 2026-03-27, this path is validated for development via DroidCam network stream.
- Windows recognizes the phone in webcam mode as `Android Webcam`, and `usbipd-win` successfully attaches it to WSL (BUSID observed as `1-7`).
- After attach, WSL enumerates camera devices (`/dev/video0` and `/dev/video1`).
- Current blocker: capture attempts still return no frame packets (`Nothing was written into output file`) even when `/dev/video0` opens and format negotiation succeeds.
- Kernel logs during stream attempts show repeated `vhci`/`usb ... Not yet implemented` messages and URB status `-104`, indicating a USBIP streaming instability for this Android webcam path in the current environment.
- DroidCam fallback pass: the phone IP endpoint was reachable from WSL (`192.168.1.2:4747`), and `ffmpeg -i http://192.168.1.2:4747/video -frames:v 1 /tmp/droidcam-test.jpg` produced a valid JPEG frame.
- Conclusion: Android phone camera is usable from WSL for development via network stream fallback. USBIP webcam mode is optional and currently unstable in this environment.

External guide assessment (custom WSL kernel approach)
- A public guide based on older Windows/WSL baselines suggests rebuilding the WSL kernel with custom USB camera config.
- In this environment, the running kernel already exposes required media and USBIP capabilities (`CONFIG_MEDIA_SUPPORT`, `CONFIG_USB_VIDEO_CLASS`, `CONFIG_USBIP_*`) and includes the `uvcvideo` module.
- Because kernel capabilities are already present and enumeration works, custom kernel rebuild is a fallback option, not the first option.
- Preferred order for this project:
    1. Modern `usbipd-win` bind/attach flow
    2. Validate stable frame delivery (`ffmpeg`/`v4l2-ctl` actual packets)
    3. If frames still never arrive, use a development fallback (network camera stream or known-good USB webcam) and keep Android-over-USB as unresolved
    4. Consider custom kernel only if all modern-path checks fail and a direct USB camera path is still required
- Avoid broad `chmod 777 /dev/video*` as a persistent practice; prefer proper group permissions (`video`) or temporary, session-scoped troubleshooting changes.

Development fallback note
- If Android-over-USB remains unstable in WSL, use a network stream bridge (for example, DroidCam/IP Webcam endpoint) for development camera testing and keep this USB path marked unresolved.

Approved path in this environment
- Preferred dev camera path: DroidCam network stream from WSL (`http://<phone-ip>:4747/video`).
- Keep USBIP webcam path as a secondary troubleshooting route until stable frame delivery is reproducible.

Failure classification
- Windows camera works but WSL sees no `/dev/video*`: not approved for WSL development.
- USB forwarding attaches the phone but no capture device appears: camera path remains blocked.
- Frame grab fails after enumeration: bridge is incomplete or unstable and should not be treated as approved.

Decision point
- If the Android USB webcam path does not yield a usable WSL capture device, document that outcome directly and choose a fallback development path later. Do not assume Windows visibility alone is sufficient.

## 4. Documentation After Validation

Only mark the workflow as approved after the speaker, microphone, and camera checks have been run.

Required updates after validation
- Update `docs/TASK_TRACKER.md` bridge task statuses and notes.
- Update `docs/phase1/WSL_AUDIO_CAMERA.md` with the exact successful commands, expected output, and troubleshooting notes.
- Update `README.md` only if the validated workflow changes the recommended WSL developer setup materially.

Suggested evidence to capture
- Date and branch name used for the checks
- Commands that passed
- Commands that failed and why
- Whether each device path is approved, blocked, or requires a fallback bridge

## Approval Matrix

| Device path | Status options | Approval rule |
|---|---|---|
| Speaker | Approved / Blocked | Must be audibly reachable from WSL through the current dev TTS path |
| Blue Yeti mic | Approved / Blocked | Must be capturable from Linux-side tooling in WSL |
| Android phone camera | Approved / Blocked / Fallback needed | Must expose a usable WSL capture path; Windows-only camera support is insufficient |

---

Last updated: 2026-03-27