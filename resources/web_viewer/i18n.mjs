// Translations of the viewer UI (English, Hungarian). Strings are plain
// text: callers put them into the DOM with textContent only.
let strings = {};
let fallback = {};
export let locale = "en";

export async function loadLocale(requested, base) {
  const pick = ["hu", "en"].includes(requested) ? requested : "en";
  const load = async (name) => {
    const response = await fetch(new URL(`locales/${name}.json`, base));
    if (!response.ok) throw new Error(`locale ${name}: HTTP ${response.status}`);
    return response.json();
  };
  // Both at once: the fallback and the map's language.
  const wanted = pick === "en" ? null : load(pick).catch(() => null);
  fallback = await load("en");
  strings = (wanted && await wanted) || fallback;
  locale = pick;
  document.documentElement.lang = pick;
  return pick;
}

export function t(key, values = {}) {
  let text = strings[key] ?? fallback[key] ?? key;
  for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, () => String(value));  // "$&" in a value stays
  return text;
}

// Locale-aware number formatting (Hungarian: space thousands, comma decimals).
export function formatNumber(value, digits) {
  const options = digits === undefined ? {} : { maximumFractionDigits: digits, minimumFractionDigits: 0 };
  return new Intl.NumberFormat(locale === "hu" ? "hu-HU" : "en-GB", options).format(value);
}
