import { neon } from "@neondatabase/serverless";
import type { DataRow } from "@/lib/api";

export async function queryArchive(statement: string, parameters: readonly unknown[] = []): Promise<DataRow[]> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) throw new Error("DATABASE_URL is missing");

  const sql = neon(databaseUrl);
  const [, rows] = await sql.transaction([
    sql.query("SELECT set_config('statement_timeout', '12000', true)"),
    sql.query(statement, [...parameters]),
  ], {
    readOnly: true,
    fetchOptions: { signal: AbortSignal.timeout(17_000) },
  });
  return rows;
}

export const archiveTable = "public.argo_profiles";
export const profileCount = "COUNT(DISTINCT (float_id, cycle_number)) FILTER (WHERE float_id IS NOT NULL AND cycle_number IS NOT NULL)";
export const countColumns = `COUNT(DISTINCT float_id)::int AS float_count,
  (${profileCount})::int AS profile_count, COUNT(*)::int AS measurement_count`;

export const metricColumns = `AVG(temperature) FILTER (WHERE temp_qc IN (1, 2)) AS average_temperature,
  AVG(salinity) FILTER (WHERE sal_qc IN (1, 2)) AS average_salinity`;

export function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function timestampOrNull(value: unknown): string | null {
  if (value instanceof Date) return value.toISOString();
  return typeof value === "string" ? value : null;
}
