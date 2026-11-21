import { z } from "zod";
import type { ChatResponse, ChatTurn } from "@/lib/api";
import { OCEAN_REGIONS } from "@/lib/ocean";

const canonicalRegions = OCEAN_REGIONS.map(({ name }) => name);
const regionNames = [...canonicalRegions].sort((a, b) => b.length - a.length);
const regionPattern = regionNames.join("|");
const regionName = new RegExp(`\\b(${regionPattern})\\b`, "gi");
const scopePattern = new RegExp(` (?:in|from|for|across|of) (?:the )?(${regionPattern}|(?:entire )?(?:archive|dataset|database))$`, "i");
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine((value) => {
  const time = Date.parse(value);
  return Number.isFinite(time) && new Date(time).toISOString().startsWith(value);
}, "Invalid calendar date");
const pressure = z.number().finite().min(0).max(12_000);
const planSchema = z.object({
  operation: z.enum(["count", "overview", "compare", "dates", "profile", "depth", "deep", "trend", "map", "track"]),
  regions: z.array(z.string().refine((name) => canonicalRegions.includes(name))).max(6).default([]),
  metric: z.enum(["temperature", "salinity", "both"]).default("both"),
  countBy: z.enum(["floats", "profiles", "measurements"]).default("measurements"),
  floatId: z.string().regex(/^\d{4,10}$/).optional(),
  cycle: z.number().int().min(0).max(9999).optional(),
  from: isoDate.optional(),
  to: isoDate.optional(),
  minPressure: pressure.optional(),
  maxPressure: pressure.optional(),
  details: z.boolean().default(false),
}).strict().refine((plan) =>
  (!plan.from || !plan.to || plan.from <= plan.to) &&
  (plan.minPressure === undefined || plan.maxPressure === undefined || plan.minPressure < plan.maxPressure) &&
  (plan.operation !== "compare" || new Set(plan.regions).size >= 2) &&
  (plan.operation !== "track" || !!plan.floatId) &&
  (plan.operation !== "deep" || plan.minPressure !== undefined)
);

export type ArchivePlan = z.infer<typeof planSchema>;

const detailPhrase = /(?:[?!.;,]\s*|\s+)(?:and )?(?:please )?(?:tell me more(?: about (?:this|that|it|the region))?(?: also)?|(?:give|show) me more (?:details|information)(?: about (?:this|that|it))?|(?:explain|describe) (?:this|that|the results?)(?: too)?|(?:tell me|give me|show me) (?:more about|more details about) (?:this|that)(?: also)?)$/;
const bareDetails = /^(?:please )?(?:tell me more(?: about (?:this|that|it|the region))?(?: also)?|(?:can you )?explain(?: (?:this|that|it|the results?))?|(?:give me )?more details(?: please)?)$/;
const mapFollowUp = /^(?:(?:show|plot) (?:this|that|it|them|the results?) on (?:a |the )?map|map (?:this|that|it|them|the results?)|(?:show me )?(?:a |the )?map)$/;

function normalize(message: string) {
  return message.toLowerCase().trim().replace(/^[\s]*(?:please\s+)?/, "").replace(/[?!.]+$/, "").replace(/\s+/g, " ");
}

function canonical(value: string) {
  return canonicalRegions.find((name) => name.toLowerCase() === value.toLowerCase());
}

function metricFor(question: string): ArchivePlan["metric"] {
  const temperature = /\b(?:temperature|temp|thermal)\b/.test(question);
  const salinity = /\bsalinity\b/.test(question);
  return temperature === salinity ? "both" : temperature ? "temperature" : "salinity";
}

export function answerConversation(message: string): ChatResponse | null {
  const question = normalize(message);
  let response: string;
  if (/^(?:wh[oi] (?:built|made|created|developed|designed) (?:you|floatchat|float chat|this(?: app)?)|who (?:is|'s) your (?:developer|creator))$/.test(question)) {
    response = "**Abuzaid** built FloatChat to make Argo ocean observations easier to explore. You can browse the [project on GitHub](https://github.com/Abuzaid-01/Float_Chat).";
  } else if (/^(?:who are you|what are you|introduce yourself|what is (?:your name|floatchat|float chat)|what (?:can you do|does floatchat do)|help|what can i ask)$/.test(question)) {
    response = "I’m **FloatChat**, an assistant for exploring archived **Argo float observations**. Ask about temperature, salinity, float positions, or how measurements change with depth.\n\nTry **“Map the float locations in the Arabian Sea”** or **“How does temperature change with depth in the Bay of Bengal?”**";
  } else if (/^(?:what (?:is|are) (?:an? )?argo(?: floats?)?|what do argo floats measure)$/.test(question)) {
    response = "**Argo floats** drift through the ocean and periodically measure a vertical profile as they rise. This archive contains temperature, salinity, pressure, time, and position. A **profile** is one float cycle’s set of readings at different pressures.";
  } else if (/^(?:hi|hey|hello)(?: floatchat)?$/.test(question)) {
    response = "Hi! I’m FloatChat. Ask me to compare two ocean regions, plot a temperature profile, or map where Argo floats were sampled.";
  } else if (/^(?:thanks|thank you)(?: floatchat)?$/.test(question)) {
    response = "You’re welcome.";
  } else {
    return null;
  }
  return { success: true, intent: "conversation", response };
}

function parseDirect(message: string) {
  let question = normalize(message);
  const details = detailPhrase.test(question);
  question = question.replace(detailPhrase, "").replace(/[?!.]+$/, "").trim();
  const scope: Partial<ArchivePlan> = { details };

  const dateRange = /\b(?:between|from) (\d{4}-\d{2}-\d{2}) (?:and|to|through) (\d{4}-\d{2}-\d{2})\b/;
  const singleDate = /\bon (\d{4}-\d{2}-\d{2})\b/;
  const year = /\b(?:in|during) ((?:19|20)\d{2})\b/;
  const interval = dateRange.exec(question);
  const single = singleDate.exec(question);
  const annual = year.exec(question);
  if (interval) {
    [, scope.from, scope.to] = interval;
    question = question.replace(dateRange, "");
  } else if (single) {
    scope.from = scope.to = single[1];
    question = question.replace(singleDate, "");
  } else if (annual) {
    scope.from = `${annual[1]}-01-01`;
    scope.to = `${annual[1]}-12-31`;
    question = question.replace(year, "");
  }

  const below = /\s+(?:deeper than|below) (\d[\d,]*(?:\.\d+)?) (?:dbar|m|meters?|metres?)\b/;
  const above = /\s+(?:shallower than|above|in the (?:top|upper)) (\d[\d,]*(?:\.\d+)?) (?:dbar|m|meters?|metres?)\b/;
  const min = below.exec(question);
  const max = above.exec(question);
  if (min) {
    scope.minPressure = Number(min[1].replaceAll(",", ""));
    question = question.replace(below, "");
  }
  if (max) {
    scope.maxPressure = Number(max[1].replaceAll(",", ""));
    question = question.replace(above, "");
  }

  question = question.replace(/\s+/g, " ").trim();
  if (/^compare\b/.test(question)) {
    const mentioned = [...new Set([...question.matchAll(regionName)].map((match) => canonical(match[1])))];
    const rest = question.replace(regionName, "region");
    if (/^compare (?:the )?(?:(?:average )?(?:temperature(?: and salinity)?|salinity)(?: between| in| across)? )?(?:the )?region(?:,? (?:with|and|versus|vs\.?|to|,) (?:the )?region)+$/.test(rest)) {
      return planSchema.safeParse({ ...scope, operation: "compare", regions: mentioned, metric: metricFor(rest) });
    }
  }

  const float = /\b(?:argo )?float(?:\s+id)?\s*#?\s*(\d{4,10})\b/;
  const floatMatch = float.exec(question);
  if (floatMatch) {
    scope.floatId = floatMatch[1];
    question = question.replace(float, "float");
  }
  const cycle = /\b(?:(?:in|for|on|at) )?cycle\s*#?\s*(\d{1,4})\b/;
  const cycleMatch = cycle.exec(question);
  if (cycleMatch) {
    scope.cycle = Number(cycleMatch[1]);
    question = question.replace(cycle, "").trim();
  }
  question = question.replace(/\s+/g, " ").trim();
  const geographical = scopePattern.exec(question);
  const region = geographical && canonical(geographical[1]);
  if (geographical) question = question.slice(0, geographical.index);
  if (region) scope.regions = [region];
  const metric = metricFor(question);
  let operation: ArchivePlan["operation"] | undefined;
  let countBy: ArchivePlan["countBy"] | undefined;

  const counts = /^(?:how many|(?:what is the )?(?:total )?number of|count) (?:argo )?(floats?|profiles?|measurements?|records?|observations?)(?: (?:are|is) there| (?:are|is)| (?:does|for|from) (?:the )?float(?: have)?)?$/;
  const counted = counts.exec(question);
  if (counted && (!/ (?:does|for|from) (?:the )?float\b/.test(question) || scope.floatId)) {
    operation = "count";
    countBy = counted[1].startsWith("float") ? "floats" : counted[1].startsWith("profile") ? "profiles" : "measurements";
  } else if (/^(?:what (?:dates does the (?:archive|dataset) cover|is the date range(?: of the (?:archive|dataset))?)|(?:show )?(?:archive |dataset )?date range)$/.test(question)) {
    operation = "dates";
  } else if (/^(?:track (?:the )?float|(?:show |plot )?(?:the )?(?:trajectory|track|path) (?:of|for) (?:the )?float|where (?:is|was|did) (?:the )?float(?: (?:go|travel))?)$/.test(question) && scope.floatId) {
    operation = "track";
  } else if (/^(?:(?:show|plot|map|list) (?:me )?(?:(?:a |the )?map of )?(?:the )?(?:argo )?float (?:locations|positions)|(?:show|plot|map) (?:me )?(?:the )?(?:argo )?floats?(?: on (?:a |the )?map)?|where are (?:the )?(?:argo )?floats(?: located)?)$/.test(question)) {
    operation = "map";
  } else if (/^(?:how does (?:average )?(?:temperature|salinity|temperature and salinity) (?:change|vary) with depth|(?:show|plot) (?:me )?(?:average )?(?:temperature|salinity|temperature and salinity) (?:by|with|vs\.?) (?:depth|pressure))$/.test(question)) {
    operation = "depth";
  } else if (/^(?:how does (?:average )?(?:temperature|salinity) (?:change|vary) over time|(?:show|plot) (?:me )?(?:the )?(?:daily (?:average )?(?:temperature|salinity|measurements?|temperature and salinity)|(?:temperature|salinity|measurements?) (?:over time|by day)|(?:temperature|salinity) trend))$/.test(question)) {
    operation = "trend";
  } else if (/^(?:show|list) (?:me )?(?:the )?profiles?$/.test(question) && scope.minPressure !== undefined) {
    operation = "deep";
  } else if (/^(?:(?:show|plot|list) (?:me )?(?:the )?(?:(?:temperature|salinity|temperature and salinity)(?: readings?| profiles?)?|(?:latest )?profiles?))(?: (?:of|for|from) (?:the )?float)?$/.test(question) && (region || scope.floatId)) {
    operation = "profile";
  } else if (/^(?:(?:what is|show(?: me)?|give me) (?:the )?(?:(?:mean|average) (?:temperature|salinity|temperature and salinity)|(?:archive |regional )?(?:summary|overview|statistics))|(?:tell me|what can you tell me|what do we know) about|summa(?:rize|rise))$/.test(question)) {
    operation = "overview";
  }
  return planSchema.safeParse({ ...scope, operation, countBy, metric });
}

function applyFollowUp(message: string, previous: ArchivePlan): ArchivePlan | null {
  const question = normalize(message);
  const regionFollowUp = /^(?:what about|and in|how about|and for) (?:the )?(.+)$/.exec(question);
  const region = regionFollowUp && canonical(regionFollowUp[1]);
  const changesMetric = regionFollowUp && /^(?:temperature|salinity)$/.test(regionFollowUp[1]);
  const { operation } = previous;
  if (mapFollowUp.test(question)) {
    return { ...previous, operation: previous.floatId ? "track" : operation === "deep" ? "deep" : "map" };
  }
  if (changesMetric) {
    return { ...previous, metric: metricFor(question), operation: ["depth", "trend", "profile", "compare"].includes(operation) ? operation : "overview" };
  }
  if (bareDetails.test(question)) return { ...previous, details: true };
  if (region) {
    return { ...previous, regions: [region], operation: operation === "compare" ? "overview" : operation };
  }
  return null;
}

export function interpretArchiveQuestion(message: string, history: ChatTurn[]): ArchivePlan | null {
  const direct = parseDirect(message);
  if (direct.success) return direct.data;

  let previous: ArchivePlan | null = null;
  for (const turn of history.slice(-12)) {
    if (turn.role !== "user") continue;
    const plan = parseDirect(turn.content);
    if (plan.success) previous = plan.data;
    else if (previous) previous = applyFollowUp(turn.content, previous) ?? previous;
  }
  return previous ? applyFollowUp(message, previous) : null;
}

export async function interpretWithGroq(message: string, history: ChatTurn[]): Promise<ArchivePlan | null> {
  const key = process.env.GROQ_API_KEY;
  if (!key) return null;

  try {
    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      signal: AbortSignal.timeout(4500),
      body: JSON.stringify({
        model: process.env.GROQ_MODEL || "openai/gpt-oss-120b",
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: `Translate questions about this Argo archive into a JSON object {"plan": object or null}. Never generate SQL or data. Set plan to null if any requested operation or filter is unsupported, scope is ambiguous, or the question is not about the archive. Fields: operation (required: count, overview, compare, dates, profile, depth, deep, trend, map, track); regions (exact strings from ${canonicalRegions.join(", ")}; omit for whole archive); metric (temperature, salinity, both); countBy (floats, profiles, measurements); floatId (digit string); cycle (integer); from and to (inclusive YYYY-MM-DD); minPressure and maxPressure (dbar, exclusive); details (boolean). Compare requires at least two regions. Depth is a vertical average, trend a daily series, deep profiles which reach past minPressure, profile recent individual casts, map last known positions, track a single float's profile positions. No forecasts, physical inference, unrecognized locations, hypothesis testing, or climatology. Use conversation only to resolve an explicit follow-up. Omit optional fields instead of returning null for fields. The latest question is last.`,
          },
          ...history.filter((turn) => turn.role === "user").slice(-3).map((turn) => ({ role: "user", content: turn.content.slice(0, 1000) })),
          { role: "user", content: message },
        ],
      }),
    });
    if (!response.ok) return null;
    const body = await response.json();
    const content = body.choices?.[0]?.message?.content;
    if (typeof content !== "string") return null;
    const parsed = planSchema.safeParse(JSON.parse(content).plan);
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}
