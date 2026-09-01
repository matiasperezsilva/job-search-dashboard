export type View = "dashboard" | "search" | "jobs" | "applications" | "profile";

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
  estado?: string;
  notas?: string;
  first_seen?: string;
  last_seen?: string;
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
      caracteres_cv?: number;
    };
  };
};
