import { useEffect, useState } from "react";
import { mergeCityMessage } from "../stream";
import type { CitySnapshot, CityStreamMessage } from "../types/city";

export function cityWebSocketUrl(location: Pick<Location, "protocol" | "host">): string {
  return `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/city`;
}

export function useCityStream() {
  const [snapshot, setSnapshot] = useState<CitySnapshot | null>(null);
  const [connectionState, setConnectionState] = useState("Connexion…");
  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let disposed = false;
    const connect = () => {
      setConnectionState("Connexion…");
      socket = new WebSocket(cityWebSocketUrl(window.location));
      socket.onopen = () => setConnectionState("Connecté");
      socket.onmessage = (message) => {
        const data = JSON.parse(message.data) as CityStreamMessage;
        setSnapshot((current) => mergeCityMessage(current, data));
      };
      socket.onerror = () => setConnectionState("Erreur de connexion");
      socket.onclose = () => {
        if (disposed) return;
        setConnectionState("Reconnexion…");
        reconnectTimer = window.setTimeout(connect, 1200);
      };
    };
    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);
  return { snapshot, connectionState };
}
