/**
 * Animated voice waveform indicator.
 * Shows animated bars when recording, a static icon when idle.
 */
import { Mic, MicOff } from "lucide-react";
import type { VoiceState } from "../hooks/useVoice";

interface Props {
  state: VoiceState;
  volume: number; // 0–1
  onClick: () => void;
}

const BAR_COUNT = 5;

export function VoiceWave({ state, volume, onClick }: Props) {
  const isRecording = state === "recording";
  const isProcessing = state === "processing";

  return (
    <button
      onClick={onClick}
      disabled={isProcessing}
      title={isRecording ? "Stop recording" : "Start voice input"}
      className={`relative flex h-10 w-10 items-center justify-center rounded-full transition-all duration-200 ${
        isRecording
          ? "bg-red-600 shadow-lg shadow-red-900/50 hover:bg-red-700"
          : isProcessing
          ? "bg-gray-600 cursor-not-allowed"
          : "bg-gray-700 hover:bg-gray-600"
      }`}
    >
      {isRecording ? (
        /* Animated bars */
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
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-transparent" />
      ) : (
        <Mic className="h-5 w-5 text-gray-300" />
      )}
    </button>
  );
}
