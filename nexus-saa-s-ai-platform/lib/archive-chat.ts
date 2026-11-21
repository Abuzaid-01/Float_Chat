import type { ChatResponse } from "@/lib/api";
import { archiveTable, countColumns, metricColumns, queryArchive, timestampOrNull } from "@/lib/archive-db";
import { formatDateRange, OCEAN_REGIONS } from "@/lib/ocean";

const regions = new Map(OCEAN_REGIONS.map(({ name }) => [name.toLowerCase(), name]));
const count = /^(?:how many|(?:what is the )?(?:total )?number of|count) (?:argo )?(floats?|profiles?|measurements?|records?|observations?)(?: (?:(?:are|is) )?(?:in|from) (?:the )?(.+?))?(?: (?:are|is) there)?$/;
const regionComparison = /^compare (?:the )?(.+?) (?:and|with|vs\.?) (?:the )?(.+)$/;
const regionReadings = /^(?:show|list) (?:the )?(temperature|salinity)(?: readings?)? in (?:the )?(.+)$/;
const pressureProfile = /^(?:show|list) (?:the )?profiles? deeper than (\d{1,4}(?:\.\d+)?) (?:dbar|m|meters?|metres?)$/;
const dateRange = /^(?:what (?:dates does the (?:archive|dataset) cover|is the date range(?: of the (?:archive|dataset))?)|(?:show )?(?:archive |dataset )?date range)$/;
const wholeArchive = new Set(["archive", "dataset", "data", "database", "total"]);

export async function answerStructured(message: string): Promise<ChatResponse | null> {
  const question = message.trim().toLowerCase().replace(/[?!\.]+$/, "").replace(/\s+/g, " ");
  const started = performance.now();

  const read = async (sql: string, parameters: unknown[], interpretation: string): Promise<ChatResponse> => {
    const data = await queryArchive(sql, parameters);
    return {
      success: true,
      response: "",
      intent: "data_query",
      route: "rules",
      interpretation,
      sql,
      data,
      result_count: data.length,
      execution_time: (performance.now() - started) / 1000,
    };
  };

  const counting = count.exec(question.replace(/ (?:are|is) there (?=(?:in|from) )/, " "));
  if (counting) {
    const [, term, scope] = counting;
    const region = scope && !wholeArchive.has(scope) ? regions.get(scope) : undefined;
    if (scope && !wholeArchive.has(scope) && !region) return null;
    const noun = term.startsWith("float") ? "floats" : term.startsWith("profile") ? "profiles" : "measurements";
    const field = noun === "floats" ? "float_count" : noun === "profiles" ? "profile_count" : "measurement_count";
    const result = await read(
      `SELECT ${countColumns} FROM ${archiveTable}${region ? " WHERE ocean_region = $1" : ""}`,
      region ? [region] : [],
      `Count ${noun} in ${region ?? "the archive"}`,
    );
    const value = result.data?.[0]?.[field];
    if (typeof value !== "number") throw new Error("Archive count was missing");
    result.response = `**${value.toLocaleString("en-US")}** ${noun} match this question.`;
    return result;
  }

  if (dateRange.test(question)) {
    const result = await read(
      `SELECT MIN(timestamp) AS earliest, MAX(timestamp) AS latest FROM ${archiveTable}`,
      [],
      "Archive date range",
    );
    const row = result.data?.[0];
    const range = formatDateRange(timestampOrNull(row?.earliest), timestampOrNull(row?.latest));
    result.response = range ? `The archive covers **${range}**.` : "The archive has no dated measurements.";
    return result;
  }

  const comparison = regionComparison.exec(question);
  if (comparison) {
    const first = regions.get(comparison[1]);
    const second = regions.get(comparison[2]);
    if (!first || !second || first === second) return null;
    const result = await read(
      `SELECT ocean_region, ${countColumns}, ${metricColumns}
       FROM ${archiveTable} WHERE ocean_region IN ($1, $2) GROUP BY ocean_region ORDER BY ocean_region`,
      [first, second],
      `Compare ${first} and ${second} using quality-controlled temperature and salinity`,
    );
    result.response = result.data?.length === 2
      ? "The table compares the regions using their archived measurements. Temperature and salinity averages use quality flags 1–2."
      : "The archive does not contain measurements for both requested regions.";
    return result;
  }

  const readings = regionReadings.exec(question);
  if (readings) {
    const region = regions.get(readings[2]);
    if (!region) return null;
    const metric = readings[1] === "temperature" ? "temperature" : "salinity";
    const flag = metric === "temperature" ? "temp_qc" : "sal_qc";
    const result = await read(
      `SELECT float_id, cycle_number, latitude, longitude, timestamp, pressure, ${metric}
       FROM ${archiveTable} WHERE ocean_region = $1 AND ${flag} IN (1, 2) AND ${metric} IS NOT NULL
       ORDER BY timestamp DESC, float_id, cycle_number, pressure LIMIT 500`,
      [region],
      `Latest quality-controlled ${metric} readings in ${region}`,
    );
    result.response = result.result_count
      ? `Showing ${result.result_count.toLocaleString("en-US")} recent ${metric} readings in **${region}**.`
      : "No observations matched those filters.";
    return result;
  }

  const deep = pressureProfile.exec(question);
  if (deep) {
    const pressure = Number(deep[1]);
    const result = await read(
      `SELECT float_id, cycle_number, MIN(timestamp) AS timestamp, MAX(pressure) AS max_pressure,
              COUNT(*)::int AS measurement_count
       FROM ${archiveTable} WHERE float_id IS NOT NULL AND cycle_number IS NOT NULL
       GROUP BY float_id, cycle_number HAVING MAX(pressure) > $1
       ORDER BY timestamp DESC, float_id, cycle_number LIMIT 500`,
      [pressure],
      `Profiles reaching deeper than ${pressure} dbar`,
    );
    result.response = result.result_count
      ? `Showing ${result.result_count.toLocaleString("en-US")} profiles that reached beyond **${pressure} dbar**.`
      : "No profiles reached the requested pressure.";
    return result;
  }

  return null;
}
