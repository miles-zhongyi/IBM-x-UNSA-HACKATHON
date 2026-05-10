import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight">Health understanding (demo)</h1>
      <p className="text-lg text-[var(--muted)]">
        Pick a role. This is a hackathon demo: not for real clinical decisions.
      </p>
      <div className="flex flex-col gap-4 sm:flex-row">
        <Link
          href="/doctor"
          className="flex min-h-touch flex-1 items-center justify-center rounded-2xl bg-blue-600 px-6 py-4 text-center text-lg font-semibold text-white"
        >
          Clinician / staff
        </Link>
        <Link
          href="/patient/marcus-demo"
          className="flex min-h-touch flex-1 items-center justify-center rounded-2xl border border-[var(--line)] bg-[var(--card)] px-6 py-4 text-center text-lg font-semibold"
        >
          Patient / caregiver
        </Link>
      </div>
      <p className="text-sm text-[var(--muted)]">
        Start the API first: <code className="rounded bg-black/5 px-1">uvicorn backend.api.main:app --reload</code>
      </p>
    </main>
  );
}
