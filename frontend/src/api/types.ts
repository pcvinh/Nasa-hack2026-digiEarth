import type { components } from './schema';

type S = components['schemas'];
export type Variable = S['Variable'];
export type Region = S['Region'];
export type RegionInput = S['RegionInput'];
export type TrendRequest = S['TrendRequest'];
export type TrendResult = S['TrendResult'];
export type TrendMap = S['TrendMap'];
export type GuideRequest = S['GuideRequest'];
export type GuideResponse = S['GuideResponse'];
export type GuideAction = S['GuideAction'];
export type Session = S['Session'];
export type SessionSummary = S['SessionSummary'];
export type SessionInput = S['SessionInput'];
export type Provenance = S['Provenance'];
export type Health = S['Health'];
export type DataStatus = S['DataStatus'];
export type Topic = S['Topic'];
/** The contract types these as number[]; the schema fixes their length, so we narrow to tuples. */
export type BBox = [west: number, south: number, east: number, north: number];
export type LonLat = [lon: number, lat: number];
export const asBBox = (b: number[]): BBox => b as BBox;
