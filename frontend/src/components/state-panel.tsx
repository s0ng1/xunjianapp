import Link from "next/link";

type StatePanelProps = {
  tone: "empty" | "error" | "info";
  title: string;
  description: string;
  action?: {
    href: string;
    label: string;
  };
};

export function StatePanel({ tone, title, description, action }: StatePanelProps) {
  return (
    <section className={`state-panel tone-${tone}`}>
      <h3 className="state-title">{title}</h3>
      <p className="state-description">{description}</p>
      {action ? (
        <div>
          <Link href={action.href} className="ghost-link">
            {action.label}
          </Link>
        </div>
      ) : null}
    </section>
  );
}
