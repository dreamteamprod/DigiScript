export interface WsMessage {
  OP: string;
  DATA: Record<string, unknown>;
  ACTION?: string;
}
