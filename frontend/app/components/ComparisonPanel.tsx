"use client";

import { useState } from "react";
import { AudioPlayer } from "./AudioPlayer";

interface ComparisonLine {
  role: "customer" | "agent";
  text: string;
  audio: string;
}

interface ComparisonPanelProps {
  withoutMemory: ComparisonLine[];
  withMemory: ComparisonLine[];
}

export function ComparisonPanel({ withoutMemory, withMemory }: ComparisonPanelProps) {
  const [memoryOn, setMemoryOn] = useState(true);

  const lines = memoryOn ? withMemory : withoutMemory;

  return (
    <section className="py-20 px-6 max-w-4xl mx-auto">
      <h2 className="text-3xl font-bold mb-4">The Callback</h2>
      <p className="text-white/50 mb-8">2 days later, Sarah calls back...</p>

      <div className="flex justify-center mb-8">
        <div className="bg-white/10 rounded-full p-1 flex">
          <button
            onClick={() => setMemoryOn(false)}
            className={`px-4 py-2 rounded-full text-sm transition-colors ${
              !memoryOn ? "bg-red-500/80 text-white" : "text-white/50"
            }`}
          >
            Memory OFF
          </button>
          <button
            onClick={() => setMemoryOn(true)}
            className={`px-4 py-2 rounded-full text-sm transition-colors ${
              memoryOn ? "bg-green-500/80 text-white" : "text-white/50"
            }`}
          >
            Memory ON
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {lines.map((line, i) => (
          <div key={`${memoryOn}-${i}`} className="flex items-start gap-3">
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
