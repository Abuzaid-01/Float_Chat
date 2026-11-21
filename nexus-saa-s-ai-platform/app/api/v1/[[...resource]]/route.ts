import { z } from "zod";
import type { BackendHealth, ChatResponse, DatabaseStats, Suggestion } from "@/lib/api";
import { answerArchive } from "@/lib/archive-chat";
import { answerConversation, interpretArchiveQuestion, interpretWithGroq } from "@/lib/archive-intent";
import { archiveTable, metricColumns, numberOrNull, profileCount, queryArchive, timestampOrNull } from "@/lib/archive-db";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ resource?: string[] }> };

const suggestions: Suggestion[] = [
  { text: "How many floats are there?", category: "statistics" },
  { text: "What is the date range of the dataset?", category: "statistics" },
  { text: "Map the float locations in the Arabian Sea", category: "geographic" },
  { text: "How does temperature change with depth in the Bay of Bengal?", category: "depth" },
  { text: "Show daily temperature in the Arabian Sea", category: "statistics" },
  { text: "Compare Arabian Sea and Bay of Bengal", category: "comparison" },
  { text: "Show profiles deeper than 1000 dbar", category: "depth" },
];

const chatRequest = z.object({
  message: z.string().trim().min(1).max(1000),
  conversation_history: z.array(z.object({
    role: z.enum(["user", "assistant"]),
    content: z.string().max(20_000),
  })).max(40).default([]),
});

class RouteError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

function archiveProblem(error: unknown) {
  const code = error && typeof error === "object" && "code" in error ? error.code : undefined;
  const name = error instanceof Error ? error.name : "UnknownError";
  console.error("FloatChat archive request failed", name, typeof code === "string" ? code : "");
  if (error instanceof Error && error.message === "DATABASE_URL is missing") return "DATABASE_URL is missing from the API environment.";
  if (code === "28P01" || code === "28000") return "Neon rejected the database credentials.";
  if (code === "42501") return "The Neon role cannot read public.argo_profiles.";
  if (code === "42P01") return "The configured database is missing public.argo_profiles.";
  if (code === "57014" || name === "TimeoutError" || name === "AbortError") return "The archive query timed out.";
  return "The API could not query the archive. Try again shortly.";
}

function failure(error: unknown) {
  if (error instanceof RouteError) return Response.json({ detail: error.message }, { status: error.status });
  return Response.json({ detail: archiveProblem(error) }, { status: 503 });
}

async function health(request: Request) {
  const result: BackendHealth = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    service: "FloatChat Netlify API",
  };
  if (new URL(request.url).searchParams.get("deep") !== "true") return Response.json(result);
  try {
    await queryArchive(`SELECT 1 FROM ${archiveTable} LIMIT 1`);
    return Response.json({ ...result, database: "reachable" });
  } catch (error) {
    return Response.json({ ...result, status: "degraded", database: "archive unavailable", detail: archiveProblem(error) });
  }
}

async function stats(): Promise<DatabaseStats> {
  const [row] = await queryArchive(
    `SELECT COUNT(*)::int AS total_records, COUNT(DISTINCT float_id)::int AS unique_floats,
            (${profileCount})::int AS profiles, MIN(timestamp) AS earliest, MAX(timestamp) AS latest,
            COUNT(DISTINCT ocean_region)::int AS regions, COUNT(DISTINCT cycle_number)::int AS cycles,
            ${metricColumns}
     FROM ${archiveTable}`,
  );
  return {
    total_records: Number(row.total_records),
    unique_floats: Number(row.unique_floats),
    profiles: Number(row.profiles),
    date_range: {
      earliest: timestampOrNull(row.earliest),
      latest: timestampOrNull(row.latest),
    },
    regions_covered: Number(row.regions),
    cycles: Number(row.cycles),
    average_temperature: numberOrNull(row.average_temperature),
    average_salinity: numberOrNull(row.average_salinity),
  };
}

async function listRegions() {
  return queryArchive(
    `SELECT ocean_region AS name, COUNT(*)::int AS measurements, COUNT(DISTINCT float_id)::int AS floats
     FROM ${archiveTable} WHERE ocean_region IS NOT NULL GROUP BY ocean_region ORDER BY measurements DESC`,
  );
}

async function floatInfo(id: string) {
  if (!/^\d{4,10}$/.test(id)) throw new RouteError(400, "Float IDs are 4 to 10 digits.");
  const [row] = await queryArchive(
    `SELECT float_id, COUNT(*)::int AS total_measurements, COUNT(DISTINCT cycle_number)::int AS total_cycles,
            MIN(timestamp) AS first_measurement, MAX(timestamp) AS last_measurement,
            AVG(latitude) AS lat, AVG(longitude) AS lon, MAX(pressure) AS max_pressure,
            MAX(ocean_region) AS ocean_region,
            MIN(temperature) FILTER (WHERE temp_qc IN (1, 2)) AS min_temp,
            MAX(temperature) FILTER (WHERE temp_qc IN (1, 2)) AS max_temp,
            MIN(salinity) FILTER (WHERE sal_qc IN (1, 2)) AS min_sal,
            MAX(salinity) FILTER (WHERE sal_qc IN (1, 2)) AS max_sal, ${metricColumns}
     FROM ${archiveTable} WHERE float_id = $1 GROUP BY float_id`,
    [id],
  );
  if (!row) throw new RouteError(404, "Float not found.");
  return {
    float_id: row.float_id,
    total_measurements: row.total_measurements,
    total_cycles: row.total_cycles,
    first_measurement: row.first_measurement,
    last_measurement: row.last_measurement,
    avg_location: { lat: numberOrNull(row.lat), lon: numberOrNull(row.lon) },
    temperature: { min: numberOrNull(row.min_temp), max: numberOrNull(row.max_temp), mean: numberOrNull(row.average_temperature) },
    salinity: { min: numberOrNull(row.min_sal), max: numberOrNull(row.max_sal), mean: numberOrNull(row.average_salinity) },
    max_pressure: numberOrNull(row.max_pressure),
    ocean_region: row.ocean_region,
  };
}

export async function GET(request: Request, { params }: RouteContext) {
  const path = (await params).resource ?? [];
  try {
    if (path.length === 2 && path[0] === "floats") return Response.json(await floatInfo(path[1]));
    if (path.length === 1) {
      switch (path[0]) {
        case "health": return health(request);
        case "stats": return Response.json(await stats());
        case "regions": return Response.json({ regions: await listRegions() });
        case "suggestions": return Response.json({ suggestions });
        case "pipeline-stats": return Response.json({ success: true, stats: { vector_store_loaded: false } });
      }
    }
    throw new RouteError(404, "Endpoint not found.");
  } catch (error) {
    return failure(error);
  }
}

async function tryLegacyChat(request: Request, input: z.infer<typeof chatRequest>): Promise<Response | null> {
  const configured = process.env.FLOATCHAT_LEGACY_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL;
  if (!configured) return null;
  try {
    const upstream = new URL("/api/v1/chat", configured);
    if (upstream.protocol !== "https:" || upstream.origin === new URL(request.url).origin) return null;
    const reply = await fetch(upstream, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      signal: AbortSignal.timeout(12_000),
      cache: "no-store",
      redirect: "error",
    });
    if (!reply.ok) return null;
    const body: ChatResponse = await reply.json();
    return typeof body.success === "boolean" && typeof body.response === "string" ? Response.json(body) : null;
  } catch {
    return null;
  }
}

export async function POST(request: Request, { params }: RouteContext) {
  const path = (await params).resource ?? [];
  if (path.length !== 1 || path[0] !== "chat") return failure(new RouteError(404, "Endpoint not found."));

  const parsed = chatRequest.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return failure(new RouteError(422, "Enter a question of 1 to 1,000 characters."));

  try {
    const { message, conversation_history: history } = parsed.data;
    const conversational = answerConversation(message);
    if (conversational) return Response.json(conversational);
    const plan = interpretArchiveQuestion(message, history);
    if (plan) return Response.json(await answerArchive(plan, "rules"));
    const modelPlan = await interpretWithGroq(message, history);
    if (modelPlan) return Response.json(await answerArchive(modelPlan, "llm"));
    const legacy = await tryLegacyChat(request, parsed.data);
    if (legacy) return legacy;
    const response = "I couldn’t turn that into an archive query. Try naming the region and the result you want, such as **“Show daily temperature in the Arabian Sea”** or **“Compare the Arabian Sea and Bay of Bengal.”**";
    return Response.json({ success: false, response, retryable: false });
  } catch (error) {
    return failure(error);
  }
}
