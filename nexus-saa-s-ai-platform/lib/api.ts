/**
 * Typed client for the FloatChat FastAPI backend (api/main.py + api/routes.py).
 *
 * Every call goes through `request`, which adds a timeout, forwards an
 * optional AbortSignal, and turns FastAPI's `{ detail }` error bodies into
 * an `ApiError` the UI can show.
 */

export type BackendHealth = {
  status: string;
  service?: string;
  timestamp?: string;
  components?: Record<string, boolean>;
};

export type DatabaseStats = {
  total_records: number;
  unique_floats: number;
  /** Distinct (float, cycle) pairs. */
  profiles?: number;
  date_range?: { earliest: string | null; latest: string | null };
  regions_covered: number;
  cycles: number;
  /** Means over good-quality values (QC 1–2); null if there are none. */
  average_temperature: number | null;
  average_salinity: number | null;
};

export type Suggestion = { text: string; category: string };

export type RegionCount = { name: string; measurements: number; floats?: number };

export type FloatInfo = {
  float_id: string;
  total_measurements: number;
  total_cycles: number;
  first_measurement: string | null;
  last_measurement: string | null;
  avg_location: { lat: number; lon: number };
  /** Good-quality values only; null when the float has none. */
  temperature: { min: number | null; max: number | null; mean: number | null };
  salinity: { min: number | null; max: number | null; mean: number | null };
  max_pressure?: number | null;
  ocean_region?: string | null;
};

export type PipelineStats = {
  success: boolean;
  error?: string;
  stats?: {
    sql_generator?: {
      total_queries: number;
      cache_hits: number;
      failed_queries: number;
      avg_complexity: number;
      cache_hit_rate: string;
      success_rate: string;
      /** How many statements came from fixed rules vs. the language model. */
      rule_built?: number;
      llm_built?: number;
    };
    vector_store_loaded?: boolean;
    vector_count?: number;
    cached_results?: number;
  };
};

export type DataRow = Record<string, unknown>;

/** Totals over everything the filters matched; `data` may be only the newest rows. */
export type ResultSummary = {
  total_matching?: number;
  floats?: number;
  profiles?: number;
  earliest?: string | null;
  latest?: string | null;
  rows_returned?: number;
  [statistic: string]: number | string | null | undefined;
};

/** Thermocline or water-mass results for the profile the question selected. */
export type ProfileAnalysis = {
  type: "thermocline" | "water_masses";
  success?: boolean;
  error?: string;
  profile?: { float_id?: string; cycle_number?: number; timestamp?: string; measurements?: number };
  thermocline_depth_dbar?: number;
  thermocline_strength_deg_per_m?: number;
  thermocline_strength_classification?: string;
  thermocline_type?: string;
  mixed_layer_depth_dbar?: number;
  surface_temp_celsius?: number;
  deep_temp_celsius?: number;
  water_masses?: Array<{
    name: string;
    core_depth_m?: number;
    depth_range_m?: [number, number];
    core_temperature_C?: number;
    core_salinity_PSU?: number;
  }>;
};

export type ChatResponse = {
  success: boolean;
  response: string;
  intent?: string;
  sql?: string | null;
  data?: DataRow[] | null;
  /** Rows the SQL returned; `data` carries at most the first 500. */
  result_count?: number;
  execution_time?: number;
  /** "rules" when fixed rules built the SQL, "llm" when the language model wrote it. */
  route?: string | null;
  /** One line saying how the question was understood. */
  interpretation?: string | null;
  summary?: ResultSummary | null;
  analysis?: ProfileAnalysis | null;
  cached?: boolean;
  error?: string | null;
};

export type ChatTurn = { role: "user" | "assistant"; content: string };

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

/** Short timeout for lookups; the chat pipeline (LLM + database) needs far longer. */
const DEFAULT_TIMEOUT_MS = 20_000;
const CHAT_TIMEOUT_MS = 120_000;

export type ApiErrorKind = "network" | "timeout" | "aborted" | "http";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;

  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

type RequestOptions = Omit<RequestInit, "signal"> & {
  signal?: AbortSignal;
  timeoutMs?: number;
};

async function readDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors arrive as a list of { msg, loc }.
    if (Array.isArray(detail)) return detail.map((item) => item?.msg).filter(Boolean).join("; ");
  } catch {
    // Body was not JSON — fall through to the status text.
  }
  return response.statusText || `Request failed (${response.status})`;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { signal, timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...init } = options;
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const onAbort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener("abort", onAbort);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...headers },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new ApiError("http", await readDetail(response), response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timedOut) {
      throw new ApiError("timeout", `No reply from the API after ${Math.round(timeoutMs / 1000)}s.`);
    }
    if (controller.signal.aborted) throw new ApiError("aborted", "Request cancelled.");
    throw new ApiError("network", `Cannot reach the FloatChat API at ${API_BASE_URL}.`);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  }
}

export const floatchatApi = {
  health: (signal?: AbortSignal) =>
    request<BackendHealth>("/api/v1/health", { signal, timeoutMs: 8_000 }),

  stats: (signal?: AbortSignal) => request<DatabaseStats>("/api/v1/stats", { signal }),

  regions: (signal?: AbortSignal) =>
    request<{ regions: RegionCount[] }>("/api/v1/regions", { signal }),

  suggestions: (signal?: AbortSignal) =>
    request<{ suggestions: Suggestion[] }>("/api/v1/suggestions", { signal }),

  pipelineStats: (signal?: AbortSignal) =>
    request<PipelineStats>("/api/v1/pipeline-stats", { signal, timeoutMs: 45_000 }),

  float: (floatId: string, signal?: AbortSignal) =>
    request<FloatInfo>(`/api/v1/floats/${encodeURIComponent(floatId)}`, { signal }),

  chat: (message: string, conversation_history: ChatTurn[], signal?: AbortSignal) =>
    request<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_history }),
      signal,
      timeoutMs: CHAT_TIMEOUT_MS,
    }),
};
