"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Row = Record<string, unknown>;

function rowLabel(r: Row) {
  const d = (r.test_date as string) || (r.visit_date as string) || "";
  return d || "?";
}

function rowValue(r: Row): number | null {
  if (typeof r.value === "number") return r.value;
  return null;
}

export function TrendChart({ data, name }: { data: Row[]; name: string }) {
  const pts = data
    .map((r) => ({
      date: rowLabel(r),
      value: rowValue(r),
    }))
    .filter((p) => p.value !== null) as { date: string; value: number }[];

  if (pts.length === 0) {
    return <p className="text-sm text-[var(--muted)]">No numeric points to chart.</p>;
  }

  return (
    <div className="mt-3 h-64 w-full rounded-xl border border-[var(--line)] bg-[var(--card)] p-2">
      <div className="mb-2 text-sm font-medium">{name}</div>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart data={pts} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
