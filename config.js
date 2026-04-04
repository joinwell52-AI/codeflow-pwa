(function (global) {
  global.BRIDGEFLOW_CONFIG = {
    appName: "BridgeFlow",
    appVersion: "1.9.6",
    relayUrl: "wss://ai.chedian.cc/bridgeflow/ws/",
    relayLabel: "公网正式中继",
    roomKey: "bridgeflow-default",
    autoConnect: true,
    defaultTarget: "PM"
  };
})(typeof self !== "undefined" ? self : window);
