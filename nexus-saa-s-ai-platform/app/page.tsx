import { Navigation } from "@/components/landing/navigation";
import { HeroSection } from "@/components/landing/hero-section";
import { ChatSection } from "@/components/landing/chat-section";
import { HowItWorksSection } from "@/components/landing/how-it-works-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { MetricsSection } from "@/components/landing/metrics-section";
import { FooterSection } from "@/components/landing/footer-section";
import { ScrollProgress } from "@/components/landing/scroll-progress";
import { Spotlight } from "@/components/landing/spotlight";
import { Marquee } from "@/components/landing/marquee";

const marqueeItems = [
  "Hybrid RAG · BM25 + FAISS",
  "1.2M+ ARGO Measurements",
  "714 Active Floats",
  "Arabian Sea · Bay of Bengal",
  "Zero SQL Hallucinations",
  "Dynamic Schema Pruning",
  "Neon PostgreSQL · Groq Llama 3.3",
];

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-x-hidden bg-background text-foreground selection:bg-primary/30 selection:text-cyan-200">
      <ScrollProgress />
      <Spotlight />
      <Navigation />
      <HeroSection />
      <Marquee items={marqueeItems} />
      <ChatSection />
      <HowItWorksSection />
      <FeaturesSection />
      <MetricsSection />
      <Marquee items={marqueeItems} className="border-b-0" />
      <FooterSection />
    </main>
  );
}