import type { ChatResponse, DataRow } from "@/lib/api";
import { archiveTable, countColumns, numberOrNull, queryArchive, timestampOrNull } from "@/lib/archive-db";
import type { ArchivePlan } from "@/lib/archive-intent";
import { formatDateRange } from "@/lib/ocean";

const exactCastTime = `TO_CHAR(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS cast_time`;
const formatCount = new Intl.NumberFormat("en-US");
const readings = ["temperature", "salinity"] as const;
const quality = { temperature: "temp_qc", salinity: "sal_qc" } as const;
const units = { temperature: "°C", salinity: "PSU" } as const;
const labels = { floats: "float_count", profiles: "profile_count", measurements: "measurement_count" } as const;

function matching(plan: ArchivePlan, omitMinimum = false) {
  const values: Array<string | string[] | number> = [];
  const clauses: string[] = [];
  if (plan.regions.length) clauses.push(`ocean_region = ANY($${values.push(plan.regions)}::text[])`);
  if (plan.floatId) clauses.push(`float_id = $${values.push(plan.floatId)}`);
  if (plan.cycle !== undefined) clauses.push(`cycle_number = $${values.push(plan.cycle)}`);
  if (plan.from) clauses.push(`timestamp >= $${values.push(plan.from)}::date`);
  if (plan.to) clauses.push(`timestamp < $${values.push(plan.to)}::date + INTERVAL '1 day'`);
  if (!omitMinimum && plan.minPressure !== undefined) clauses.push(`pressure > $${values.push(plan.minPressure)}`);
  if (plan.maxPressure !== undefined) clauses.push(`pressure < $${values.push(plan.maxPressure)}`);
  return {
    values,
    where: (...additional: string[]) => {
      const filters = [...clauses, ...additional];
      return filters.length ? ` WHERE ${filters.join(" AND ")}` : "";
    },
  };
}

function scopeText(plan: ArchivePlan) {
  const where = plan.regions.join(" and ");
  const date = plan.from && plan.to
    ? plan.from === plan.to ? plan.from : `${plan.from} through ${plan.to}`
    : plan.from ? `from ${plan.from}` : plan.to ? `through ${plan.to}` : "";
  return [
    plan.floatId ? `float ${plan.floatId}` : null,
    plan.cycle !== undefined ? `cycle ${plan.cycle}` : null,
    where || null,
    date || null,
    plan.minPressure !== undefined ? `deeper than ${plan.minPressure} dbar` : null,
    plan.maxPressure !== undefined ? `shallower than ${plan.maxPressure} dbar` : null,
  ].filter(Boolean).join(" · ") || "the archive";
}

function metricValue(row: DataRow, metric: typeof readings[number]) {
  const value = numberOrNull(row[`average_${metric}`]);
  return value === null ? null : `${value.toFixed(2)} ${units[metric]}`;
}

function quantities(row: DataRow) {
  const count = (key: string) => formatCount.format(Number(row[key]));
  return `**${count("measurement_count")}** measurements across **${count("profile_count")}** profiles from **${count("float_count")}** distinct floats`;
}

function positionStatement(where: string) {
  return `SELECT float_id, cycle_number, latitude, longitude, timestamp, ocean_region, ${exactCastTime}
    FROM (
      SELECT DISTINCT ON (float_id) float_id, cycle_number, latitude, longitude, timestamp, ocean_region
      FROM ${archiveTable}${where}
      ORDER BY float_id, timestamp DESC, cycle_number DESC, pressure
    ) AS positions ORDER BY timestamp DESC, float_id LIMIT 250`;
}

export async function answerArchive(plan: ArchivePlan, route: "rules" | "llm"): Promise<ChatResponse> {
  const start = performance.now();
  const scope = scopeText(plan);
  const metrics = plan.metric === "both" ? readings : [plan.metric];
  const averages = metrics.map((metric) =>
    `AVG(${metric}) FILTER (WHERE ${quality[metric]} IN (1, 2)) AS average_${metric}`,
  ).join(", ");
  const { values, where } = matching(plan, plan.operation === "deep");

  const read = async (
    sql: string,
    interpretation: string,
    explain: (rows: DataRow[]) => string,
    evidence?: { mapSql?: string; view?: "map" | "chart"; trajectory?: boolean; comparison?: { sql: string; bandSize: number; mapLimit: number } },
  ): Promise<ChatResponse> => {
    const [data, map_data, depthRows] = await Promise.all([
      queryArchive(sql, values),
      evidence?.mapSql ? queryArchive(evidence.mapSql, values).catch(() => undefined) : undefined,
      evidence?.comparison ? queryArchive(evidence.comparison.sql, values).catch(() => undefined) : undefined,
    ]);
    return {
      success: true,
      response: explain(data),
      intent: "data_query",
      route,
      interpretation: `${interpretation} · ${scope}`,
      sql,
      data,
      map_data,
      comparison: evidence?.comparison && {
        depth_rows: depthRows,
        band_size: evidence.comparison.bandSize,
        map_limit_per_region: evidence.comparison.mapLimit,
      },
      preferred_view: evidence?.view,
      trajectory: evidence?.trajectory,
      result_count: data.length,
      execution_time: (performance.now() - start) / 1000,
    };
  };

  if (plan.operation === "count" || plan.operation === "overview" || plan.operation === "dates") {
    const sql = `SELECT ${countColumns}, MIN(timestamp) AS earliest, MAX(timestamp) AS latest,
       ${averages}, MIN(pressure) AS min_pressure, MAX(pressure) AS max_pressure
       FROM ${archiveTable}${where()}`;
    const explain = ([row]: DataRow[]) => {
      if (!row || !Number(row.measurement_count)) return `The archive has no measurements matching **${scope}**.`;
      const range = formatDateRange(timestampOrNull(row.earliest), timestampOrNull(row.latest));
      const subject = plan.regions.length || plan.floatId || plan.from || plan.to || plan.minPressure !== undefined || plan.maxPressure !== undefined
        ? `For **${scope}**, the archive contains` : "The archive contains";
      if (plan.operation === "dates" && !plan.details) {
        return range ? `The observations matching **${scope}** span **${range}** (UTC).` : "The matching measurements have no recorded dates.";
      }
      const amount = formatCount.format(Number(row[labels[plan.countBy]]));
      if (plan.operation === "count" && !plan.details) {
        const supporting = plan.countBy === "measurements"
          ? ` They come from **${formatCount.format(Number(row.float_count))}** distinct floats.` : "";
        return `${subject} **${amount}** ${plan.countBy}.${supporting}`;
      }
      const numbers = metrics.flatMap((metric) => {
        const value = metricValue(row, metric);
        return value ? [`**${value}** mean ${metric}`] : [];
      });
      return [
        `${subject} ${quantities(row)}.`,
        range && `The measurements span **${range}** (UTC).`,
        row.min_pressure != null && row.max_pressure != null &&
          `The observed pressure range is **${formatCount.format(Number(row.min_pressure))}–${formatCount.format(Number(row.max_pressure))} dbar**.`,
        numbers.length > 0 && `Quality-controlled readings have ${numbers.join(" and ")}. These are averages over the matched readings across sampled depths.`,
        plan.details && "A profile is one float cycle; it can contain many individual readings at different pressures.",
      ].filter(Boolean).join(" ");
    };
    const mapSql = (plan.details || plan.operation === "overview") && plan.regions.length
      ? positionStatement(where("float_id IS NOT NULL", "latitude IS NOT NULL", "longitude IS NOT NULL"))
      : undefined;
    return read(sql, plan.operation === "count" ? `Count ${plan.countBy}` : plan.operation === "dates" ? "Observation dates" : "Archive summary",
      explain, { mapSql, view: plan.details && mapSql ? "map" : undefined });
  }

  if (plan.operation === "compare") {
    const mapLimit = Math.floor(400 / plan.regions.length);
    const bandSize = 100;
    const qcCounts = metrics.map((metric) =>
      `COUNT(${metric}) FILTER (WHERE ${quality[metric]} IN (1, 2))::int AS ${metric}_readings`,
    ).join(", ");
    const castMeans = metrics.map((metric) =>
      `AVG(average_${metric}) AS average_${metric}, STDDEV_SAMP(average_${metric}) AS ${metric}_cast_sd,
       COUNT(average_${metric})::int AS ${metric}_casts,
       SUM(${metric}_readings)::int AS ${metric}_readings`,
    ).join(", ");
    const depthSql = `WITH casts AS (
      SELECT ocean_region, float_id, cycle_number, timestamp,
             FLOOR(pressure / ${bandSize})::int * ${bandSize} AS depth_bin, ${averages}, ${qcCounts}
      FROM ${archiveTable}${where("float_id IS NOT NULL", "cycle_number IS NOT NULL", "timestamp IS NOT NULL", "pressure >= 0")}
      GROUP BY ocean_region, float_id, cycle_number, timestamp, depth_bin
    )
    SELECT ocean_region, depth_bin, ${castMeans}
    FROM casts GROUP BY ocean_region, depth_bin ORDER BY ocean_region, depth_bin`;
    const mapSql = `WITH casts AS (
      SELECT DISTINCT ON (ocean_region, float_id, cycle_number, timestamp)
             ocean_region, float_id, cycle_number, timestamp, latitude, longitude
      FROM ${archiveTable}${where("float_id IS NOT NULL", "cycle_number IS NOT NULL", "timestamp IS NOT NULL", "latitude BETWEEN -90 AND 90", "longitude BETWEEN -180 AND 180")}
      ORDER BY ocean_region, float_id, cycle_number, timestamp, pressure
    ), ranked AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY ocean_region ORDER BY timestamp, float_id, cycle_number) AS position_index,
             COUNT(*) OVER (PARTITION BY ocean_region) AS region_total
      FROM casts
    )
    SELECT ocean_region, float_id, cycle_number, timestamp, latitude, longitude, ${exactCastTime}
    FROM ranked WHERE (position_index - 1) % CEIL(region_total::numeric / ${mapLimit}) = 0
    ORDER BY ocean_region, timestamp, float_id, cycle_number`;
    return read(
      `SELECT ocean_region, ${countColumns}, ${averages}, ${qcCounts},
              MIN(timestamp) AS earliest, MAX(timestamp) AS latest,
              MIN(pressure) AS min_pressure, MAX(pressure) AS max_pressure
       FROM ${archiveTable}${where()} GROUP BY ocean_region ORDER BY ocean_region`,
      "Compare archived measurements by region",
      (rows) => {
        if (!rows.length) return "The archive has no observations matching the requested comparison.";
        const descriptions = rows.map((row) => {
          const parts = metrics.flatMap((metric) => {
            const value = metricValue(row, metric);
            return value ? [`${value} mean ${metric}`] : [];
          });
          return `- **${row.ocean_region}** had ${formatCount.format(Number(row.measurement_count))} measurements from ${formatCount.format(Number(row.float_count))} floats${parts.length ? `, with ${parts.join(" and ")}` : ""}.`;
        });
        const found = new Set(rows.map((row) => row.ocean_region));
        const missing = plan.regions.filter((region) => !found.has(region));
        return [
          ...descriptions,
          "",
          missing.length ? `No matching observations for ${missing.join(", ")}.` : "",
          "These means pool readings across the sampled pressures. Open **By depth** for a like-pressure comparison and **Coverage** to check the sample sizes and dates.",
        ].join("\n");
      },
      { mapSql, comparison: { sql: depthSql, bandSize, mapLimit } },
    );
  }

  if (plan.operation === "map" || plan.operation === "track") {
    const locations = where("float_id IS NOT NULL", "latitude IS NOT NULL", "longitude IS NOT NULL");
    const tracking = plan.operation === "track";
    const sql = tracking
      ? `SELECT * FROM (
           SELECT float_id, cycle_number, timestamp, ${exactCastTime}, MAX(ocean_region) AS ocean_region,
                  AVG(latitude) AS latitude, AVG(longitude) AS longitude
           FROM ${archiveTable}${locations}
           GROUP BY float_id, cycle_number, timestamp ORDER BY timestamp DESC, cycle_number DESC LIMIT 500
         ) AS track ORDER BY timestamp, cycle_number`
      : positionStatement(locations);
    return read(sql, tracking ? "Float trajectory from recorded positions" : "Last recorded position per float",
      (rows) => {
        if (!rows.length) return `No recorded float positions match **${scope}**.`;
        const range = formatDateRange(timestampOrNull(rows[0].timestamp), timestampOrNull(rows[rows.length - 1].timestamp));
        if (tracking) {
          return `The map shows **${rows.length}** recorded positions for **float ${plan.floatId}**${range ? ` from **${range}**` : ""}.` +
            (rows.length > 1 ? " The line connects observations in time order. The float’s exact path between observations is unknown." : "");
        }
        return `The map shows the latest recorded position for each of **${rows.length}** matching floats${rows.length === 250 ? " (limited to 250 floats)" : ""}. These are archived observations.`;
      }, { view: "map", trajectory: tracking });
  }

  if (plan.operation === "depth" || plan.operation === "trend") {
    const depth = plan.operation === "depth";
    return read(
      `SELECT ${depth ? "FLOOR(pressure / 100)::int * 100 AS depth_bin" : "timestamp::date::text AS day"},
            ${averages}, COUNT(*)::int AS measurement_count
       FROM ${archiveTable}${where()} GROUP BY 1 ORDER BY 1`,
      depth ? "Mean readings per 100 dbar pressure band" : "Daily archive observations",
      (rows) => {
        if (!rows.length) return `No archive observations match **${scope}**.`;
        if (!depth) {
          const sum = rows.reduce((total, row) => total + Number(row.measurement_count), 0);
          const changes = metrics.flatMap((metric) => {
            const valid = rows.filter((row) => metricValue(row, metric) !== null);
            if (valid.length < 2) return [];
            return [`Mean ${metric} was **${metricValue(valid[0], metric)}** on the first day with valid readings and **${metricValue(valid[valid.length - 1], metric)}** on the last.`];
          });
          return [`The chart covers **${rows.length}** sampled UTC days for **${scope}**, with **${formatCount.format(sum)}** measurements.`, ...changes].join(" ");
        }
        const profileSummary = metrics.flatMap((metric) => {
          const valid = rows.filter((row) => metricValue(row, metric) !== null);
          if (!valid.length) return [];
          const shallow = valid[0];
          const deep = valid[valid.length - 1];
          return [valid.length === 1
            ? `Mean ${metric} was **${metricValue(shallow, metric)}** in the sampled ${shallow.depth_bin}–${Number(shallow.depth_bin) + 100} dbar band.`
            : `Mean ${metric} was **${metricValue(shallow, metric)}** in the shallowest sampled band (${shallow.depth_bin}–${Number(shallow.depth_bin) + 100} dbar) and **${metricValue(deep, metric)}** in the deepest (${deep.depth_bin}–${Number(deep.depth_bin) + 100} dbar).`];
        });
        return [`For **${scope}**, the profile chart groups quality-controlled readings into **100 dbar** pressure bands.`, ...profileSummary].join(" ");
      },
      {
        view: "chart",
        mapSql: plan.regions.length ? positionStatement(where("float_id IS NOT NULL", "latitude IS NOT NULL", "longitude IS NOT NULL")) : undefined,
      },
    );
  }

  if (plan.operation === "deep") {
    const threshold = `$${values.push(plan.minPressure!)}`;
    return read(
      `SELECT float_id, cycle_number, MIN(timestamp) AS timestamp, TO_CHAR(MIN(timestamp), 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS cast_time, AVG(latitude) AS latitude,
              AVG(longitude) AS longitude, MAX(pressure) AS max_pressure, COUNT(*)::int AS measurement_count
       FROM ${archiveTable}${where("float_id IS NOT NULL", "cycle_number IS NOT NULL")}
       GROUP BY float_id, cycle_number HAVING MAX(pressure) > ${threshold}
       ORDER BY timestamp DESC, float_id, cycle_number LIMIT 500`,
      "Profiles reaching the requested pressure",
      (rows) => rows.length
        ? `Showing **${rows.length}** recent profiles that reached beyond **${plan.minPressure} dbar**. Open the map to see where they were recorded.`
        : "No profiles reached the requested pressure within those filters.",
    );
  }

  const measurements = metrics.map((metric) => `CASE WHEN ${quality[metric]} IN (1, 2) THEN ${metric} END AS ${metric}`).join(", ");
  const usable = metrics.map((metric) => `(${quality[metric]} IN (1, 2) AND ${metric} IS NOT NULL)`).join(" OR ");
  return read(
    `WITH selected AS (
       SELECT float_id, cycle_number, timestamp FROM ${archiveTable}${where("float_id IS NOT NULL", "cycle_number IS NOT NULL", `(${usable})`)}
       GROUP BY float_id, cycle_number, timestamp ORDER BY timestamp DESC, float_id, cycle_number LIMIT 3
     )
     SELECT float_id, cycle_number, timestamp, ${exactCastTime}, latitude, longitude, pressure, ${measurements}
     FROM ${archiveTable} JOIN selected USING (float_id, cycle_number, timestamp)
     ${where(`(${usable})`).trimStart()}
     ORDER BY timestamp DESC, float_id, cycle_number, pressure LIMIT 4500`,
    "Recent individual float profiles",
    (rows) => {
      if (!rows.length) return `No quality-controlled profile readings match **${scope}**.`;
      const count = new Set(rows.map((row) => `${row.float_id}/${row.cycle_number}/${row.timestamp}`)).size;
      return `The chart shows **${formatCount.format(rows.length)}** quality-controlled readings from **${count}** recent ${count === 1 ? "profile" : "profiles"} for **${scope}**. Switch to **Map** for the locations of these casts.`;
    },
    { view: "chart" },
  );
}
