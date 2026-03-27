"use client";

const steps = [
  {
    number: "1",
    title: "Post-Call Webhook",
    description:
      "ElevenLabs fires a webhook after each call ends. Your server receives the transcript, caller ID, and extracted data collection fields.",
  },
  {
    number: "2",
    title: "Store by Caller",
    description:
      "The webhook handler upserts a memory record keyed by phone number. Each field (name, issue, order ID) is persisted for future calls.",
  },
  {
    number: "3",
    title: "Inject via Dynamic Variables",
    description:
      "On the next inbound call, the conversation-initiation webhook responds with dynamic_variables — the agent greets the caller by name and already knows their context.",
  },
];

const webhookPython = `from flask import Flask, request
import json

app = Flask(__name__)
memory_store: dict[str, dict] = {}

@app.post("/webhook/post-call")
def post_call():
    body = request.get_json()
    caller = body["caller_id"]          # e.g. "+14155550100"
    data   = body["data_collection"]    # ElevenLabs extracted fields

    memory_store[caller] = {
        "name":     data.get("customer_name"),
        "issue":    data.get("issue_summary"),
        "order_id": data.get("order_id"),
    }
    return {"status": "ok"}`;

const dynamicVariablesJson = `// POST /webhook/conversation-init
// ElevenLabs calls this before connecting the caller.

{
  "dynamic_variables": {
    "customer_name":  "Sarah Chen",
    "last_issue":     "Double-charged for premium plan",
    "order_id":       "ORD-4521",
    "returning":      "true"
  }
}`;

function CodeBlock({ code, label }: { code: string; label: string }) {
  const lines = code.split("\n").map((line, i) => {
    // Colour strings (quoted values) green, dict/object keys blue
    const coloured = line
      .replace(
        /("(?:[^"\\]|\\.)*")\s*:/g,
        '<span class="text-blue-400">$1</span>:'
      )
      .replace(
        /:\s*("(?:[^"\\]|\\.)*")/g,
        ': <span class="text-green-400">$1</span>'
      )
      .replace(
        /(#.*$)/,
        '<span class="text-white/40">$1</span>'
      );

    return (
      <span key={i} dangerouslySetInnerHTML={{ __html: coloured + "\n" }} />
    );
  });

  return (
    <div className="flex-1 min-w-0">
      <p className="text-xs text-white/40 uppercase tracking-wider mb-2 font-mono">
        {label}
      </p>
      <div className="bg-black/40 border border-white/10 rounded-lg p-4 overflow-x-auto">
        <pre className="font-mono text-sm text-white/80 leading-relaxed whitespace-pre">
          {lines}
        </pre>
      </div>
    </div>
  );
}

export function HowItWorks() {
  return (
    <section className="py-20 px-6 max-w-5xl mx-auto">
      <h2 className="text-3xl font-bold mb-2">How It Works</h2>
      <p className="text-white/50 mb-12">
        Three webhooks. Zero extra infrastructure.
      </p>

      {/* Step cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-16 relative">
        {steps.map((step, idx) => (
          <div key={step.number} className="flex flex-col gap-4">
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 flex-1">
              <div className="w-9 h-9 rounded-full bg-white/10 border border-white/20 flex items-center justify-center font-mono font-bold text-white mb-4">
                {step.number}
              </div>
              <h3 className="font-semibold text-white mb-2">{step.title}</h3>
              <p className="text-white/50 text-sm leading-relaxed">
                {step.description}
              </p>
            </div>

            {/* Arrow between cards (hidden on last) */}
            {idx < steps.length - 1 && (
              <div className="hidden md:flex absolute top-1/2 -translate-y-1/2 text-white/20 text-xl pointer-events-none select-none"
                style={{ left: `calc(${(idx + 1) * 33.33}% - 12px)` }}>
                →
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Code snippets */}
      <div className="flex flex-col md:flex-row gap-6">
        <CodeBlock
          label="webhook handler — Python (Flask)"
          code={webhookPython}
        />
        <CodeBlock
          label="conversation-init response — JSON"
          code={dynamicVariablesJson}
        />
      </div>
    </section>
  );
}
