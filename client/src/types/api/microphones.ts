export interface Microphone {
  id: number;
  show_id: number | null;
  name: string | null;
  description: string | null;
}

export interface MicrophoneAllocation {
  mic_id: number;
  scene_id: number;
  character_id: number;
}
