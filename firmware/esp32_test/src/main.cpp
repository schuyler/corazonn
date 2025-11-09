#include <Arduino.h>

const int LED_PIN = 2;          // Built-in LED on GPIO 2
const int SENSOR_PIN = 12;      // PulseSensor on GPIO 12 (ADC2 - testing only, won't work with WiFi)

const int THRESHOLD = 2200;     // Adjust based on observed values
const int SAMPLE_RATE_MS = 20;  // 50Hz for pulse detection
const int REFRACTORY_MS = 300;  // Min 300ms between beats (~200 BPM max)
const int LED_FLASH_MS = 50;    // LED on duration

bool lastAboveThreshold = false;
unsigned long lastBeatTime = 0;

void setup() {
    Serial.begin(115200);
    delay(100);
    Serial.println("PulseSensor Pulse Detection Starting...");
    Serial.println("Threshold: 2200");

    pinMode(LED_PIN, OUTPUT);
    pinMode(SENSOR_PIN, INPUT);
}

void loop() {
    int raw = analogRead(SENSOR_PIN);

    // Turn off LED after flash duration (always check this)
    if (millis() - lastBeatTime > LED_FLASH_MS) {
        digitalWrite(LED_PIN, LOW);
    }

    // Ignore saturated values (connection/disconnection artifacts)
    if (raw >= 4095) {
        lastAboveThreshold = false;
        delay(SAMPLE_RATE_MS);
        return;
    }

    bool currentlyAbove = (raw > THRESHOLD);

    // Rising edge detection with refractory period
    if (currentlyAbove && !lastAboveThreshold) {
        if (millis() - lastBeatTime > REFRACTORY_MS) {
            digitalWrite(LED_PIN, HIGH);
            lastBeatTime = millis();

            Serial.print("BEAT! Value: ");
            Serial.println(raw);
        }
    }

    lastAboveThreshold = currentlyAbove;
    delay(SAMPLE_RATE_MS);
}
