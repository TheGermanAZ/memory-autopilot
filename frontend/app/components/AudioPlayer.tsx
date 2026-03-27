"use client";

import { useRef, useState } from "react";

interface AudioPlayerProps {
  src: string;
  size?: "sm" | "md";
}

export function AudioPlayer({ src, size = "sm" }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      audio.currentTime = 0;
      setPlaying(false);
    } else {
      audio.play();
      setPlaying(true);
    }
  };

  return (
    <>
      <audio
        ref={audioRef}
        src={src}
        onEnded={() => setPlaying(false)}
        preload="none"
      />
      <button
        onClick={toggle}
        className={`inline-flex items-center justify-center rounded-full transition-colors ${
          size === "sm" ? "w-7 h-7 text-xs" : "w-9 h-9 text-sm"
        } ${
          playing
            ? "bg-white text-black"
            : "bg-white/10 text-white hover:bg-white/20"
        }`}
        aria-label={playing ? "Stop" : "Play"}
      >
        {playing ? "■" : "▶"}
      </button>
    </>
  );
}
