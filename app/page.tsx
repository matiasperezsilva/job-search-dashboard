export const dynamic = "force-dynamic";

import AppClient from "../components/AppClient";

export default function Home() {
  const supabaseUrl = process.env.SUPABASE_URL || "";
  const supabaseKey = process.env.SUPABASE_PUBLISHABLE_KEY || "";
  return <AppClient supabaseUrl={supabaseUrl} supabaseKey={supabaseKey} />;
}
