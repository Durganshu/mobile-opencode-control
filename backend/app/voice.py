import io
import os
import tempfile
from dataclasses import dataclass

from .config import Settings


class VoiceError(RuntimeError):
    pass


@dataclass
class BuiltinSynthesisResult:
    audio_bytes: bytes
    mimetype: str
    model: str


class BuiltinVoiceRuntime:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._stt_model = None
        self._tts_model = None

    def _load_stt_model(self):
        if self._stt_model is not None:
            return self._stt_model

        try:
            from faster_whisper import WhisperModel
        except Exception as exc:
            raise VoiceError(
                "Built-in STT is unavailable. Install backend dependencies for faster-whisper."
            ) from exc

        try:
            self._stt_model = WhisperModel(
                self.settings.builtin_stt_model,
                device=self.settings.builtin_stt_device,
                compute_type=self.settings.builtin_stt_compute_type,
            )
        except Exception as exc:
            raise VoiceError(f"Failed to load built-in STT model: {exc}") from exc

        return self._stt_model

    def _load_tts_model(self):
        if self._tts_model is not None:
            return self._tts_model

        try:
            from TTS.api import TTS
        except Exception as exc:
            raise VoiceError(
                "Built-in TTS is unavailable. Install backend dependencies for Coqui TTS."
            ) from exc

        try:
            self._tts_model = TTS(
                model_name=self.settings.builtin_tts_model,
                progress_bar=False,
                gpu=False,
            )
        except Exception as exc:
            raise VoiceError(f"Failed to load built-in TTS model: {exc}") from exc

        return self._tts_model

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> tuple[str, str]:
        model = self._load_stt_model()
        suffix = os.path.splitext(filename or "recording.webm")[-1] or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()

            try:
                segments, _ = model.transcribe(
                    temp_audio.name,
                    language=language or None,
                    vad_filter=True,
                )
            except Exception as exc:
                raise VoiceError(f"Failed to transcribe audio: {exc}") from exc

            transcript_parts = [
                segment.text.strip() for segment in segments if segment.text
            ]
            transcript = " ".join(part for part in transcript_parts if part).strip()
            return transcript, self.settings.builtin_stt_model

    def synthesize(self, text: str, voice: str | None = None) -> BuiltinSynthesisResult:
        model = self._load_tts_model()

        kwargs = {"text": text}
        selected_speaker = (voice or "").strip() or self.settings.builtin_tts_speaker
        if selected_speaker:
            kwargs["speaker"] = selected_speaker

        selected_language = self.settings.builtin_tts_language.strip()
        if selected_language:
            kwargs["language"] = selected_language

        try:
            wav = model.tts(**kwargs)
        except TypeError:
            kwargs.pop("language", None)
            kwargs.pop("speaker", None)
            wav = model.tts(text=text)
        except Exception as exc:
            raise VoiceError(f"Failed to synthesize speech: {exc}") from exc

        try:
            import soundfile as sf

            buffer = io.BytesIO()
            sf.write(buffer, wav, 22050, format="WAV")
            audio_bytes = buffer.getvalue()
        except Exception as exc:
            raise VoiceError(f"Failed to encode synthesized audio: {exc}") from exc

        return BuiltinSynthesisResult(
            audio_bytes=audio_bytes,
            mimetype="audio/wav",
            model=self.settings.builtin_tts_model,
        )
