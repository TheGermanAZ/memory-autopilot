"use client";

import { useEffect, useState } from "react";

interface MemoryCardProps {
  memory: Record<string, string>;
}

export function MemoryCard({ memory }: MemoryCardProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.3 }
    );
    const el = document.getElementById("memory-card");
    if (el) observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const jsonStr = JSON.stringify(memory, null, 2);

  return (
    <section id="memory-card" className="py-20 px-6 max-w-3xl mx-auto">
      <h2 className="text-3xl font-bold mb-4">What Memory Autopilot Extracted</h2>
      <p className="text-white/50 mb-8">
        Extracted automatically by ElevenLabs Data Collection after the call.
      </p>
      <div
        className={`bg-white/5 border border-white/10 rounded-lg p-6 font-mono text-sm transition-all duration-1000 ${
          visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
        }`}
      >
        <pre className="text-green-400 whitespace-pre-wrap">{jsonStr}</pre>
      </div>
    </section>
  );
}
