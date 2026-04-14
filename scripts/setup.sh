#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE_FILE="$ROOT_DIR/.env.example"

prompt_yes_no() {
  local prompt="$1"
  local default_answer="${2:-y}"
  local suffix="[Y/n]"
  if [[ "$default_answer" == "n" ]]; then
    suffix="[y/N]"
  fi

  while true; do
    read -r -p "$prompt $suffix " reply
    reply="${reply:-$default_answer}"
    case "${reply,,}" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) echo "Please answer y or n." ;;
    esac
  done
}

set_env_value() {
  local key="$1"
  local value="$2"

  python3 - "$ENV_FILE" "$key" "$value" <<'PY'
import pathlib
import sys

env_path = pathlib.Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
line = f"{key}={value}"

if env_path.exists():
    lines = env_path.read_text().splitlines()
else:
    lines = []

for index, existing in enumerate(lines):
    if existing.startswith(f"{key}="):
        lines[index] = line
        env_path.write_text("\n".join(lines) + "\n")
        raise SystemExit(0)

lines.append(line)
env_path.write_text("\n".join(lines) + "\n")
PY
}

require_command() {
  local command_name="$1"
  local install_hint="$2"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: $command_name"
    echo "$install_hint"
    exit 1
  fi
}

echo "== Mobile OpenCode Control setup =="

require_command "python3" "Install Python 3.11+ and re-run setup."
require_command "npm" "Install Node.js + npm and re-run setup."
require_command "curl" "Install curl and re-run setup."

if ! command -v opencode >/dev/null 2>&1; then
  echo "OpenCode CLI was not found in PATH."
  if prompt_yes_no "Install OpenCode CLI now using the official installer?" "y"; then
    bash -lc 'curl -fsSL https://opencode.ai/install | bash'
  else
    echo "OpenCode CLI is required. Install it, then re-run this script."
    exit 1
  fi
fi

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$ROOT_DIR/.venv"
fi

echo "Installing backend dependencies..."
"$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip
"$ROOT_DIR/.venv/bin/python" -m pip install -r "$ROOT_DIR/backend/requirements.txt"

echo "Installing frontend dependencies..."
if [[ -f "$ROOT_DIR/frontend/package-lock.json" ]]; then
  npm --prefix "$ROOT_DIR/frontend" ci
else
  npm --prefix "$ROOT_DIR/frontend" install
fi

if [[ -f "$ENV_FILE" ]]; then
  if prompt_yes_no ".env already exists. Keep current file and only update selected keys?" "y"; then
    :
  else
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
  fi
else
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
fi

echo
echo "Voice provider setup"
echo "1) Built-in CPU voice (Coqui TTS + faster-whisper)"
echo "2) External OpenAI-compatible endpoints"
echo "3) Auto fallback (external if configured, else built-in)"
read -r -p "Select voice mode [1/2/3] (default 1): " voice_choice
voice_choice="${voice_choice:-1}"

case "$voice_choice" in
  1)
    set_env_value "VOICE_PROVIDER_MODE" "builtin"
    set_env_value "STT_BASE_URL" ""
    set_env_value "STT_API_KEY" ""
    set_env_value "TTS_BASE_URL" ""
    set_env_value "TTS_API_KEY" ""
    ;;
  2)
    set_env_value "VOICE_PROVIDER_MODE" "external"
    read -r -p "STT base URL (OpenAI-compatible /v1): " stt_base_url
    read -r -p "STT API key (leave empty if not required): " stt_api_key
    read -r -p "STT model [whisper-1]: " stt_model
    stt_model="${stt_model:-whisper-1}"

    read -r -p "TTS base URL (OpenAI-compatible /v1): " tts_base_url
    read -r -p "TTS API key (leave empty if not required): " tts_api_key
    read -r -p "TTS model [gpt-4o-mini-tts]: " tts_model
    tts_model="${tts_model:-gpt-4o-mini-tts}"
    read -r -p "TTS voice [alloy]: " tts_voice
    tts_voice="${tts_voice:-alloy}"

    set_env_value "STT_BASE_URL" "$stt_base_url"
    set_env_value "STT_API_KEY" "$stt_api_key"
    set_env_value "STT_MODEL" "$stt_model"
    set_env_value "TTS_BASE_URL" "$tts_base_url"
    set_env_value "TTS_API_KEY" "$tts_api_key"
    set_env_value "TTS_MODEL" "$tts_model"
    set_env_value "TTS_VOICE" "$tts_voice"
    ;;
  3)
    set_env_value "VOICE_PROVIDER_MODE" "auto"
    read -r -p "Optional STT base URL (leave empty for built-in fallback): " stt_base_url
    read -r -p "Optional STT API key: " stt_api_key
    read -r -p "STT model [whisper-1]: " stt_model
    stt_model="${stt_model:-whisper-1}"
    read -r -p "Optional TTS base URL (leave empty for built-in fallback): " tts_base_url
    read -r -p "Optional TTS API key: " tts_api_key
    read -r -p "TTS model [gpt-4o-mini-tts]: " tts_model
    tts_model="${tts_model:-gpt-4o-mini-tts}"
    read -r -p "TTS voice [alloy]: " tts_voice
    tts_voice="${tts_voice:-alloy}"

    set_env_value "STT_BASE_URL" "$stt_base_url"
    set_env_value "STT_API_KEY" "$stt_api_key"
    set_env_value "STT_MODEL" "$stt_model"
    set_env_value "TTS_BASE_URL" "$tts_base_url"
    set_env_value "TTS_API_KEY" "$tts_api_key"
    set_env_value "TTS_MODEL" "$tts_model"
    set_env_value "TTS_VOICE" "$tts_voice"
    ;;
  *)
    echo "Invalid voice selection. Exiting without changing env voice settings."
    exit 1
    ;;
esac

read -r -p "Built-in STT model [small.en]: " builtin_stt_model
builtin_stt_model="${builtin_stt_model:-small.en}"
read -r -p "Built-in STT compute type [int8]: " builtin_stt_compute
builtin_stt_compute="${builtin_stt_compute:-int8}"
read -r -p "Built-in TTS model [tts_models/en/ljspeech/tacotron2-DDC]: " builtin_tts_model
builtin_tts_model="${builtin_tts_model:-tts_models/en/ljspeech/tacotron2-DDC}"

set_env_value "BUILTIN_STT_MODEL" "$builtin_stt_model"
set_env_value "BUILTIN_STT_COMPUTE_TYPE" "$builtin_stt_compute"
set_env_value "BUILTIN_STT_DEVICE" "cpu"
set_env_value "BUILTIN_TTS_MODEL" "$builtin_tts_model"

read -r -p "Default project root folder (optional, absolute path): " default_project_root
set_env_value "DEFAULT_PROJECT_ROOT" "$default_project_root"

if prompt_yes_no "Install/refresh systemd autostart services now?" "n"; then
  echo "You may be prompted for sudo password."
  sudo "$ROOT_DIR/scripts/install-autostart-ubuntu.sh"
fi

echo
echo "Setup complete."
echo "- Env file: $ENV_FILE"
echo "- Start locally: ./scripts/start-app.sh"
echo "- Stop locally:  ./scripts/stop-app.sh"
