import Link from "next/link";
import { ThemeProvider } from "../components/ThemeProvider";
import Header from "../components/Header";
import Hero from "../components/Hero";
import FeatureStepCard from "../components/FeatureStepCard";
import ConsolePreview from "../components/ConsolePreview";
import Footer from "../components/Footer";


const STEPS = [
  { n: "1", t: "Classify", d: "Task type, complexity and capability detected." },
  { n: "2", t: "Route", d: "Cheapest capable model wins the policy gates." },
  { n: "3", t: "Execute", d: "Provider adapters run with retry + failover." },
  { n: "4", t: "Evaluate", d: "Quality judged; one strong escalation max." },
];

export default function Home() {
  return (
    <ThemeProvider>
      <Header />
      <main className="flex flex-col items-center gap-12 py-12">
        <Hero />
        <section className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 max-w-5xl">
          {STEPS.map((s) => (
            <FeatureStepCard key={s.n} step={s} />
          ))}
        </section>
        <ConsolePreview />
      </main>
      <Footer />
    </ThemeProvider>
  );
}
