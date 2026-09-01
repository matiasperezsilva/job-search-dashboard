import React from "react";

type Props = { size?: number; className?: string };
const svg = (children: React.ReactNode, { size = 20, className }: Props = {}) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);
export const HomeIcon = (p: Props) => svg(<><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/></>, p);
export const SearchIcon = (p: Props) => svg(<><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>, p);
export const BriefcaseIcon = (p: Props) => svg(<><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M3 12h18"/></>, p);
export const CheckIcon = (p: Props) => svg(<><path d="M20 6 9 17l-5-5"/></>, p);
export const FileIcon = (p: Props) => svg(<><path d="M14 2H6a2 2 0 0 0-2 2v16h16V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h6"/></>, p);
export const ExternalIcon = (p: Props) => svg(<><path d="M14 3h7v7"/><path d="M10 14 21 3"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/></>, p);
export const SparkIcon = (p: Props) => svg(<><path d="m12 3 1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z"/><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/></>, p);
export const LogoutIcon = (p: Props) => svg(<><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/></>, p);
export const UploadIcon = (p: Props) => svg(<><path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 20h16"/></>, p);
export const ArrowRightIcon = (p: Props) => svg(<><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>, p);
export const RefreshIcon = (p: Props) => svg(<><path d="M20 6v5h-5"/><path d="M4 18v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 9M5.5 15A7 7 0 0 0 18 17.5l2-2.5"/></>, p);
