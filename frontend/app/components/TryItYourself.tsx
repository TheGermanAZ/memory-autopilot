"use client";

import { useState } from "react";

const SAMPLE_TRANSCRIPT = `Customer: Hi, my name is Sarah Chen. I'm calling about my March invoice — I was charged twice for the premium plan.
Agent: I'm sorry to hear that, Sarah. Can you give me your order number?
Customer: It's ORD-4521. This is really frustrating.`;

export function TryItYourself() {
  const [transcript, setTranscript] = useState(SAMPLE_TRANSCRIPT);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExtract() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/demo/extract`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ transcript }),
        }
      );

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const json = await res.json();
      setResult(json);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="py-20 px-6 max-w-5xl mx-auto">
      <h2 className="text-3xl font-bold mb-2">Try It Yourself</h2>

      {/* Label */}
      <p className="text-xs text-white/40 uppercase tracking-wider mb-8 font-mono border border-white/10 rounded px-3 py-1.5 inline-block">
        Demo extraction endpoint — the production system uses ElevenLabs native
        Data Collection.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Input */}
        <div className="flex flex-col gap-4">
          <label className="text-sm text-white/60 font-medium">
            Paste a call transcript
          </label>
          <textarea
            className="flex-1 min-h-[220px] bg-white/5 border border-white/10 rounded-lg p-4 font-mono text-sm text-white/80 placeholder-white/20 resize-none focus:outline-none focus:border-white/30 transition-colors leading-relaxed"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste a call transcript here…"
          />
          <button
            onClick={handleExtract}
            disabled={loading || !transcript.trim()}
            className="self-start px-5 py-2.5 bg-white text-black font-semibold text-sm rounded-lg hover:bg-white/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {loading ? "Extracting…" : "Extract Memory"}
          </button>
        </div>

        {/* Right: Output */}
        <div className="flex flex-col gap-4">
          <label className="text-sm text-white/60 font-medium">
            Extraction result
          </label>
          <div className="flex-1 min-h-[220px] bg-black/40 border border-white/10 rounded-lg p-4 overflow-auto">
            {loading && (
              <div className="flex items-center gap-2 text-white/40 text-sm font-mono">
                <span className="animate-pulse">●</span>
                <span>Waiting for response…</span>
              </div>
            )}

            {error && !loading && (
              <p className="text-red-400 text-sm font-mono">{error}</p>
            )}

            {result && !loading && (
              <pre className="font-mono text-sm text-green-400 whitespace-pre-wrap leading-relaxed">
                {JSON.stringify(result, null, 2)}
              </pre>
            )}

            {!result && !loading && !error && (
              <p className="text-white/20 text-sm font-mono">
                Results will appear here…
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
