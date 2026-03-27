"use client";

import { AudioPlayer } from "./AudioPlayer";

interface TranscriptLine {
  role: "customer" | "agent";
  text: string;
  audio: string;
}

interface TranscriptPanelProps {
  title: string;
  lines: TranscriptLine[];
}

export function TranscriptPanel({ title, lines }: TranscriptPanelProps) {
  return (
    <section className="py-20 px-6 max-w-3xl mx-auto">
      <h2 className="text-3xl font-bold mb-8">{title}</h2>
      <div className="space-y-4">
        {lines.map((line, i) => (
          <div key={i} className="flex items-start gap-3">
            <AudioPlayer src={`/audio/${line.audio}`} />
            <div>
              <span
                className={`text-sm font-semibold ${
                  line.role === "customer" ? "text-blue-400" : "text-green-400"
                }`}
              >
                {line.role === "customer" ? "Customer" : "Agent"}:
              </span>
              <p className="text-white/80 mt-0.5">{line.text}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
