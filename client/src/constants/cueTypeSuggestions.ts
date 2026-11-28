export interface SuggestedCueType {
  prefix: string;
  description: string;
  colour: string;
}

/** Common cue types offered on a first visit, before any exist. */
export const SUGGESTED_CUE_TYPES: SuggestedCueType[] = [
  { prefix: 'LX', description: 'Lighting', colour: '#ffd23f' },
  { prefix: 'SND', description: 'Sound', colour: '#2563c9' },
  { prefix: 'FLY', description: 'Flys', colour: '#a8327f' },
  { prefix: 'VID', description: 'Video', colour: '#17744f' },
];
