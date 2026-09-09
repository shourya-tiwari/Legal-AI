import { Mail } from "lucide-react";
import { GithubIcon, LinkedinIcon } from "@/components/shared/brand-icons";
import { MarketingHero, Section } from "@/components/marketing/section";
import { Button } from "@/components/ui/button";

export const metadata = { title: "Contact" };

const LINKS = [
  {
    icon: GithubIcon,
    label: "GitHub",
    value: "shourya-tiwari/Legal-AI",
    href: "https://github.com/shourya-tiwari/Legal-AI",
  },
  {
    icon: LinkedinIcon,
    label: "LinkedIn",
    value: "Connect",
    href: "https://www.linkedin.com/",
  },
  {
    icon: Mail,
    label: "Email",
    value: "tshourya1507@gmail.com",
    href: "mailto:tshourya1507@gmail.com",
  },
];

export default function ContactPage() {
  return (
    <>
      <MarketingHero
        eyebrow="Contact"
        title="Get in touch"
        description="This is a portfolio / final-year engineering project. The best way to reach out is GitHub or email."
      />
      <Section className="max-w-2xl">
        <div className="grid gap-4 sm:grid-cols-3">
          {LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              target="_blank"
              rel="noreferrer"
              className="flex flex-col items-center gap-2 rounded-xl border border-border bg-surface p-6 text-center transition-colors hover:border-border-strong"
            >
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary-muted text-primary">
                <l.icon className="size-5" />
              </div>
              <p className="text-sm font-medium">{l.label}</p>
              <p className="text-xs text-muted-foreground">{l.value}</p>
            </a>
          ))}
        </div>
        <div className="mt-8 flex justify-center">
          <Button asChild>
            <a href="mailto:tshourya1507@gmail.com">
              <Mail /> Send an email
            </a>
          </Button>
        </div>
      </Section>
    </>
  );
}
