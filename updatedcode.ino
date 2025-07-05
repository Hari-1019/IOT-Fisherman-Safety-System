#include <WiFi.h>
#include <FirebaseESP32.h>
#include <DHT.h> 
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>
#include <math.h>

// === WiFi & Firebase Configuration ===
#define WIFI_SSID "Dialog 4G 582"
#define WIFI_PASSWORD "A99d09d1"
#define FIREBASE_HOST "esp32-iot-project-c74d7-default-rtdb.asia-southeast1.firebasedatabase.app"
#define FIREBASE_AUTH "nbRsESjTDUoy0dsANkRFEjOkasPrzR5Wz2QDWKxg"

// === Firebase Setup ===
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// === Pin Definitions ===
#define DHTPIN 4
#define DHTTYPE DHT11
#define BUZZER_PIN 25
#define BUTTON_PIN 27

// === Sensor and Module Objects ===
DHT dht(DHTPIN, DHTTYPE);
Adafruit_MPU6050 mpu;
TinyGPSPlus gps;
HardwareSerial GPSserial(1); // UART1: RX=16, TX=17

// === Geofence Settings ===
double fixedLat = 0.0, fixedLon = 0.0;
bool locationFixed = false;
bool isBuzzing = false;
const double GEOFENCE_RADIUS = 40.0; // meters

void setup() {
  Serial.begin(115200);
  GPSserial.begin(9600, SERIAL_8N1, 16, 17); // GPS RX=16, TX=17

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(BUZZER_PIN, LOW);

  dht.begin(); // Start DHT11
  if (!mpu.begin()) {
    Serial.println("MPU6050 not found!");
    while (1);
  }

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("🔌 Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected");

  config.database_url = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  Serial.println("Firebase Connected");

  Serial.println("All sensors initialized");
  fixLocation(); // Lock GPS base location
}

void loop() {
  monitorLocation();  // GPS and geofence
  readDHT();          // Temp and humidity
  checkMotion();      // Crash or flip
  checkButton();      // Distress button
  delay(2000);        // Wait before next cycle
}

// === Lock Initial GPS Location ===
void fixLocation() {
  Serial.println("Searching for GPS fix...");
  while (!gps.location.isValid()) {
    while (GPSserial.available()) gps.encode(GPSserial.read());
    Serial.println("Still searching...");
    delay(1000);
  }

  fixedLat = gps.location.lat();
  fixedLon = gps.location.lng();
  locationFixed = true;

  Serial.printf("Location fixed: %.6f, %.6f\n", fixedLat, fixedLon);
}

// === Monitor GPS and Geofence ===
void monitorLocation() {
  while (GPSserial.available()) gps.encode(GPSserial.read());

  if (!gps.location.isValid()) {
    Serial.println("📡 Waiting for GPS signal...");
    return;
  }

  double lat = gps.location.lat();
  double lon = gps.location.lng();
  double dist = TinyGPSPlus::distanceBetween(lat, lon, fixedLat, fixedLon);

  Serial.printf("Location: %.6f, %.6f | Distance: %.2f m\n", lat, lon, dist);

  Firebase.setFloat(fbdo, "/gps/latitude", lat);
  Firebase.setFloat(fbdo, "/gps/longitude", lon);
  Firebase.setFloat(fbdo, "/gps/distance", dist);

  if (dist > GEOFENCE_RADIUS && !isBuzzing) {
    Serial.println("OUTSIDE geofence!");
    triggerAlert("🚧 OUTSIDE geofence!");
    Firebase.setString(fbdo, "/alerts/geofence", "Exited geofence");
    isBuzzing = true;
  } else if (dist <= GEOFENCE_RADIUS && isBuzzing) {
    Serial.println("✅ Back inside geofence.");
    digitalWrite(BUZZER_PIN, LOW);
    isBuzzing = false;
  }
}

// === Read Temperature and Humidity ===
void readDHT() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("DHT11 read failed");
    return;
  }

  Serial.printf("Humidity: %.1f %% | 🌡 Temp: %.1f °C\n", humidity, temperature);

  Firebase.setFloat(fbdo, "/sensor/temperature", temperature);
  Firebase.setFloat(fbdo, "/sensor/humidity", humidity);
}

// === Detect Crash or Flip ===
void checkMotion() {
  sensors_event_t a, g, t;
  mpu.getEvent(&a, &g, &t);

  float ax = a.acceleration.x;
  float ay = a.acceleration.y;
  float az = a.acceleration.z;
  float magnitude = sqrt(ax * ax + ay * ay + az * az);

  Serial.printf("Accel → X: %.2f | Y: %.2f | Z: %.2f | Mag: %.2f\n", ax, ay, az, magnitude);

  Firebase.setFloat(fbdo, "/accelerometer/x", ax);
  Firebase.setFloat(fbdo, "/accelerometer/y", ay);
  Firebase.setFloat(fbdo, "/accelerometer/z", az);
  Firebase.setFloat(fbdo, "/accelerometer/magnitude", magnitude);

  if (az < -8.0) triggerAlert("Boat flipped!");
  if (magnitude > 12.0 || magnitude < 1.0) triggerAlert("⚠ Crash or abnormal stop!");
}

// === Check Distress Button ===
void checkButton() {
  if (digitalRead(BUTTON_PIN) == LOW) {
    triggerAlert("Distress button pressed!");
    Firebase.setString(fbdo, "/alerts/button", "Distress triggered");
  }
}

// === Trigger Buzzer and Alert Upload ===
void triggerAlert(String message) {
  Serial.println(message);
  digitalWrite(BUZZER_PIN, HIGH);
  delay(2000);
  digitalWrite(BUZZER_PIN, LOW);
  Firebase.setString(fbdo, "/alerts/latest", message);
}



