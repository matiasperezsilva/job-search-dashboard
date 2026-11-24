export const dynamic = "force-dynamic";

import AppClient from "../../../components/AppClient";
import {supabasePublicConfig} from "../../../lib/supabase-public-config";

export default function UpdatePasswordPage() {
  return <AppClient {...supabasePublicConfig()} forceRecovery />;
}
