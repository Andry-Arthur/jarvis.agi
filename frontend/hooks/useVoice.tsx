"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiUrl } from "../lib/apiBase";

export type VoiceState = "idle" | "recording" | "processing" | "speaking";

interface UseVoiceOptions {
  onTranscript: (text: string) => void;
}

export function useVoice({ onTranscript }: UseVoiceOptions) {
  const [state, setState] = useState<VoiceState>("idle");
  const [volume, setVolume] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const stopVolumeMeter = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    setVolume(0);
  }, []);

  const startVolumeMeter = useCallback((stream: MediaStream) => {
    const ctx = new AudioContext();
    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    src.connect(analyser);
    analyserRef.current = analyser;

    const data = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteFrequencyData(data);
      const avg = data.reduce((a, b) => a + b, 0) / data.length;
      setVolume(avg / 128);
      animFrameRef.current = requestAnimationFrame(tick);
    };
    tick();
  }, []);

  const startRecording = useCallback(async () => {
    if (state !== "idle") return;
    setState("recording");
    chunksRef.current = [];

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    startVolumeMeter(stream);

    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = async () => {
      stopVolumeMeter();
      setState("processing");

      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("file", blob, "recording.webm");

      try {
        const res = await fetch(apiUrl("/api/voice/transcribe"), {
          method: "POST",
          body: formData,
        });
        const { text } = await res.json();
        if (text?.trim()) onTranscript(text.trim());
      } catch {
        // ignore
      } finally {
        setState("idle");
      }
    };

    recorder.start(250);
  }, [state, startVolumeMeter, stopVolumeMeter, onTranscript]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const toggleRecording = useCallback(() => {
    if (state === "recording") stopRecording();
    else startRecording();
  }, [state, startRecording, stopRecording]);

  useEffect(() => {
    return () => {
      stopVolumeMeter();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [stopVolumeMeter]);

  return { state, volume, toggleRecording };
}

