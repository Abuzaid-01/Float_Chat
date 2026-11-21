import type { DataRow } from "@/lib/api";

export function downloadRows(rows: DataRow[], filename: string) {
  if (!rows.length) return;
  const columns = Object.keys(rows[0]);
  const cell = (value: unknown) => {
    const text = value == null ? "" : String(value);
    const safe = typeof value === "string" && /^\s*[=+@-]/.test(text) ? `'${text}` : text;
    return /[",\r\n]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
  };
  const csv = [columns.map(cell).join(","), ...rows.map((row) => columns.map((column) => cell(row[column])).join(","))].join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
