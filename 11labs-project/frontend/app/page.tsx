import { TranscriptPanel } from "./components/TranscriptPanel";
import { MemoryCard } from "./components/MemoryCard";
import { ComparisonPanel } from "./components/ComparisonPanel";
import { HowItWorks } from "./components/HowItWorks";
import { TryItYourself } from "./components/TryItYourself";

const call1Lines = [
  { role: "customer" as const, text: "Hi, my name is Sarah Chen. I'm calling about my March invoice — I was charged twice for the premium plan.", audio: "call1_customer_01.mp3" },
  { role: "agent" as const, text: "I'm sorry to hear that, Sarah. Can you give me your order number?", audio: "call1_agent_01.mp3" },
  { role: "customer" as const, text: "It's ORD-4521. This is really frustrating, I've been a customer for two years and this is the second time this has happened.", audio: "call1_customer_02.mp3" },
  { role: "agent" as const, text: "I understand your frustration. Let me look into order ORD-4521. I can see the duplicate charge. I'm going to escalate this to our billing team and they'll process a refund within 48 hours.", audio: "call1_agent_02.mp3" },
  { role: "customer" as const, text: "Okay, thank you. Please make sure someone actually follows up this time.", audio: "call1_customer_03.mp3" },
  { role: "agent" as const, text: "Absolutely, Sarah. I've noted that follow-up is important to you. You'll hear from us within 48 hours. Is there anything else I can help with?", audio: "call1_agent_03.mp3" },
  { role: "customer" as const, text: "No, that's all. Thank you.", audio: "call1_customer_04.mp3" },
];

const call2WithoutMemory = [
  { role: "agent" as const, text: "Thank you for calling support, how can I help you today?", audio: "call2_no_mem_agent_01.mp3" },
  { role: "customer" as const, text: "Hi, this is Sarah Chen. I called two days ago about a double charge on my account.", audio: "call2_no_mem_customer_01.mp3" },
  { role: "agent" as const, text: "I'm sorry to hear that. Can you tell me your order number and what the issue was?", audio: "call2_no_mem_agent_02.mp3" },
  { role: "customer" as const, text: "It's ORD-4521. I was charged twice for the premium plan. Someone was supposed to process a refund.", audio: "call2_no_mem_customer_02.mp3" },
];

const call2WithMemory = [
  { role: "agent" as const, text: "Hi Sarah, welcome back. I can see you called two days ago about a double charge on order ORD-4521. Let me check on the status of your refund.", audio: "call2_mem_agent_01.mp3" },
  { role: "customer" as const, text: "Oh wow, yes, that's exactly right. Has the refund been processed?", audio: "call2_mem_customer_01.mp3" },
  { role: "agent" as const, text: "It looks like the refund was processed yesterday. Can you check your account to confirm you see it?", audio: "call2_mem_agent_02.mp3" },
  { role: "customer" as const, text: "Let me check... yes, I see it. Thank you so much for following up.", audio: "call2_mem_customer_02.mp3" },
];

const extractedMemory = {
  customer_name: "Sarah Chen",
  issue_type: "billing",
  issue_summary: "Double charged for premium plan",
  order_id: "ORD-4521",
  customer_sentiment: "frustrated",
  open_actions: "Refund pending — follow up within 48 hours",
};

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center text-center py-32 px-6 max-w-4xl mx-auto">
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6">
          Memory Autopilot
        </h1>
        <p className="text-xl md:text-2xl text-white/70 mb-4 max-w-2xl">
          Automatic cross-session memory for ElevenLabs voice agents.
        </p>
        <p className="text-lg text-white/40 mb-12 max-w-xl">
          Your agents forget every caller. This fixes that.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          <a
            href="#demo"
            className="px-6 py-3 bg-white text-black font-semibold rounded-lg hover:bg-white/90 transition-colors"
          >
            See the demo ↓
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 border border-white/20 text-white font-semibold rounded-lg hover:bg-white/5 transition-colors"
          >
            View on GitHub
          </a>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* First call transcript */}
      <div id="demo">
        <TranscriptPanel title="The First Call" lines={call1Lines} />
      </div>

      {/* Transition text */}
      <div className="flex flex-col items-center justify-center py-16 px-6">
        <div className="w-px h-12 bg-white/10 mb-6" />
        <p className="text-white/30 text-lg font-mono tracking-widest uppercase">
          2 days later...
        </p>
        <div className="w-px h-12 bg-white/10 mt-6" />
      </div>

      {/* Memory card */}
      <MemoryCard memory={extractedMemory} />

      {/* Comparison panel */}
      <ComparisonPanel
        withoutMemory={call2WithoutMemory}
        withMemory={call2WithMemory}
      />

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* How It Works */}
      <HowItWorks />

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* Try It Yourself */}
      <TryItYourself />

      {/* Footer */}
      <footer className="border-t border-white/10 py-10 px-6 text-center">
        <p className="text-white/30 text-sm">
          Built by German Alvarez &nbsp;·&nbsp;{" "}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white/60 transition-colors underline underline-offset-4"
          >
            GitHub
          </a>
        </p>
      </footer>
    </main>
  );
}
