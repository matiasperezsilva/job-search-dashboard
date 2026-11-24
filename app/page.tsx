export const dynamic = "force-dynamic";

import AppClient from "../components/AppClient";
import {supabasePublicConfig} from "../lib/supabase-public-config";

export default function Home() {
  return <AppClient {...supabasePublicConfig()} />;
}
