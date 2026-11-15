/** Display rounding only. No scientific values are computed here. */
export const NA = '—';

export function fmtSig(x: number | null | undefined, sig = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return NA;
  if (x === 0) return '0';
  return Number(x.toPrecision(sig)).toString();
}

export function fmtSigned(x: number | null | undefined, sig = 2): string {
  const s = fmtSig(x, sig);
  return s !== NA && x! > 0 ? `+${s}` : s;
}

export function fmtP(p: number | null | undefined): string {
  if (p === null || p === undefined) return NA;
  if (p < 0.001) return 'p < 0.001';
  return `p = ${p.toFixed(2)}`;
}
