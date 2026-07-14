/*
 * ESP-01 (ESP8266) MQTT bridge for the STM32 energy node.
 *
 * The STM32 sends one line per message over UART @115200:
 *     <topic> <json>\n
 * This sketch parses the line and publishes <json> to <topic>. It owns Wi-Fi
 * and MQTT (reconnect handled here); the STM32 stays a dumb JSON emitter.
 *
 * Board:   "Generic ESP8266 Module" (ESP-01, 1 MB)
 * Library: PubSubClient (Nick O'Leary) via Library Manager
 * Wiring:  ESP RX <- STM32 PA9 (TX),  ESP TX -> STM32 PA10 (RX), common GND,
 *          dedicated 3.3 V supply (AMS1117 + 470 uF) — NOT the Black Pill pin.
 */
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// ---- edit these ----------------------------------------------------
static const char *WIFI_SSID = "your-ssid";
static const char *WIFI_PASS = "your-pass";
static const char *MQTT_HOST = "192.168.0.10";
static const uint16_t MQTT_PORT = 1883;
static const char *MQTT_CLIENT_ID = "stm32_0001";
// --------------------------------------------------------------------

WiFiClient net;
PubSubClient mqtt(net);

static String line;

static void ensureConnected() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    while (WiFi.status() != WL_CONNECTED) delay(250);
  }
  while (!mqtt.connected()) {
    // LWT: broker marks us offline if the link drops.
    if (mqtt.connect(MQTT_CLIENT_ID,
                     "energy/stm32_0001/status", 0, true,
                     "{\"schema_version\":\"1.0\",\"device_id\":"
                     "\"stm32_0001\",\"status\":\"offline\"}")) {
      break;
    }
    delay(1000);
  }
}

static void handleLine(const String &l) {
  int sp = l.indexOf(' ');
  if (sp <= 0) return;
  String topic = l.substring(0, sp);
  String payload = l.substring(sp + 1);
  mqtt.publish(topic.c_str(), payload.c_str());
}

void setup() {
  Serial.begin(115200);          // UART to the STM32
  WiFi.mode(WIFI_STA);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(512);       // telemetry JSON headroom
  line.reserve(512);
}

void loop() {
  ensureConnected();
  mqtt.loop();

  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      handleLine(line);
      line = "";
    } else if (c != '\r') {
      line += c;
    }
  }
}
