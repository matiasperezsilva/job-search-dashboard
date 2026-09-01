export type View = "dashboard" | "search" | "jobs" | "applications" | "profile";

export type MatchComponent = {
  label: string;
  value: number;
  max?: number;
  detail?: string;
  kind?: "positive" | "negative" | "neutral";
};

export type MatchBreakdown = {
  version?: number;
  verdict?: string;
  components?: MatchComponent[];
  pre_clamp_score?: number;
  final_score?: number;
  area?: string;
  matched_roles?: string[];
  matched_skills?: string[];
};

export type Job = {
  id: string;
  titulo: string;
  empresa?: string;
  descripcion?: string;
  modalidad?: string;
  link?: string;
  fuente?: string;
  puntaje: number;
  area?: string;
  razon?: string;
  match_breakdown?: MatchBreakdown;
  estado?: string;
  notas?: string;
  first_seen?: string;
  last_seen?: string;
  published_at?: string | null;
  favorite?: boolean;
  hidden?: boolean;
  hidden_at?: string | null;
};

export type DashboardData = {
  total: number;
  top: number;
  postuladas: number;
  entrevistas: number;
  sources: { name: string; count: number }[];
  recent: Job[];
};

export type ProfileData = {
  active: boolean;
  cv_name?: string;
  profile?: {
    resumen?: {
      areas_detectadas?: string[];
      skills_detectadas?: string[];
      terminos_busqueda?: string[];
      roles_objetivo?: string[];
      seniority_estimado?: string;
      anos_experiencia?: number | null;
      caracteres_cv?: number;
    };
    preferencias?: {
      modalidades?: string[];
      ubicaciones?: string[];
      renta_minima?: number | null;
      moneda?: string;
    };
  };
};


export type SearchRun = {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress?: { message?: string; current_source?: string; source_index?: number; source_total?: number; source_states?: Record<string,{status:string; cantidad?:number; segundos?:number; error?:string}> };
  result?: any;
  error?: string;
};

