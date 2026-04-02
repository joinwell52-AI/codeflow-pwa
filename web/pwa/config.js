(function (global) {
  global.BRIDGEFLOW_CONFIG = {
    appName: "BridgeFlow",
    appVersion: "1.6.0",
    relayUrl: "wss://relay.example.com/bridgeflow/ws/",
    relayLabel: "示例公网中继",
    roomKey: "replace-with-random-room-key",
    autoConnect: false,
    defaultTarget: "PM"
  };
})(typeof self !== "undefined" ? self : window);
