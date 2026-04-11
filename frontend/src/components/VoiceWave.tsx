/**
 * Animated voice waveform indicator.
 * Shows animated bars when recording, a static icon when idle.
 */
import { Mic } from "lucide-react";
import type { VoiceState } from "../hooks/useVoice";

interface Props {
  state: VoiceState;
  volume: number; // 0–1
  isSpeaking?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

const BAR_COUNT = 5;

export function VoiceWave({
  state,
  volume,
  isSpeaking = false,
  disabled = false,
  onClick,
}: Props) {
  const isRecording = state === "recording";
  const isProcessing = state === "processing";
  const showSpeakingRing = !isRecording && !isProcessing && isSpeaking;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isProcessing || disabled}
      title={
        isRecording
          ? "Stop recording"
          : isProcessing
          ? "Transcribing…"
          : isSpeaking
          ? "JARVIS is speaking"
          : "Voice input"
      }
      className={`relative flex h-10 w-10 items-center justify-center rounded-full transition-all duration-200 ${
        isRecording
          ? "bg-jarvis-500 shadow-lg shadow-jarvis-500/35 ring-2 ring-jarvis-300/80 hover:bg-jarvis-600"
          : isProcessing
          ? "cursor-not-allowed bg-surface-muted"
          : showSpeakingRing
          ? "bg-surface ring-2 ring-jarvis-400 ring-offset-2 ring-offset-page animate-pulse hover:bg-surface-muted"
          : "border border-border bg-surface hover:bg-surface-muted"
      } ${disabled && !isRecording ? "opacity-50" : ""}`}
    >
      {isRecording ? (
        <div className="flex items-center gap-[2px]">
          {Array.from({ length: BAR_COUNT }).map((_, i) => (
            <span
              key={i}
              className="block w-[3px] rounded-full bg-white"
              style={{
                height: `${12 + volume * 16 * Math.sin((Date.now() / 200 + i) % Math.PI)}px`,
                animation: `wave ${0.8 + i * 0.15}s ease-in-out infinite`,
                animationDelay: `${i * 0.1}s`,
              }}
            />
          ))}
        </div>
      ) : isProcessing ? (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-jarvis-500 border-t-transparent" />
      ) : (
        <Mic className={`h-5 w-5 ${showSpeakingRing ? "text-jarvis-600" : "text-muted"}`} />
      )}
    </button>
  );
}
