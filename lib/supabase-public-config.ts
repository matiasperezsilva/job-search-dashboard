export function supabasePublicConfig() {
  const supabaseUrl = process.env.SUPABASE_URL?.trim() || "";
  const key = process.env.SUPABASE_PUBLISHABLE_KEY?.trim() || "";
  if (key.startsWith("sb_publishable_")) return {supabaseUrl, supabaseKey: key};

  // Supabase projects may still use a legacy JWT for the public anon key.
  try {
    const payload = JSON.parse(Buffer.from(key.split(".")[1], "base64url").toString("utf8"));
    if (payload?.role === "anon") return {supabaseUrl, supabaseKey: key};
  } catch {
    // Any other key or configuration error must stay on the server.
  }
  return {supabaseUrl, supabaseKey: ""};
}
